#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小説画像化ツール - 共通ユーティリティモジュール
色変換・透過変換・ファイル名補助・その他共通処理
"""

import os
import re
from pathlib import Path
from typing import Tuple, Union, Optional


def ensure_directory_exists(directory: Union[str, Path]) -> Path:
    """
    ディレクトリが存在しない場合は作成する

    Args:
        directory: 作成するディレクトリのパス

    Returns:
        Path: 作成されたディレクトリのPathオブジェクト
    """
    path = Path(directory)
    path.mkdir(parents=True, exist_ok=True)
    return path


def hex_to_rgba(hex_color: str, alpha: int = 255) -> Tuple[int, int, int, int]:
    """
    HEX色コードをRGBA形式に変換

    Args:
        hex_color: HEX色コード（例: "#FF0000", "#ff0000", "FF0000"）
        alpha: アルファ値（0-255）

    Returns:
        Tuple[int, int, int, int]: RGBA値のタプル

    Raises:
        ValueError: 無効なHEX色コードの場合
    """
    # #記号を除去し、大文字に統一
    hex_color = hex_color.lstrip("#").upper()

    # 3文字の短縮形を6文字に展開（例: "F0A" -> "FF00AA"）
    if len(hex_color) == 3:
        hex_color = "".join([c * 2 for c in hex_color])

    # 6文字のHEXコードかチェック
    if len(hex_color) != 6 or not all(
        c in "0123456789ABCDEF" for c in hex_color
    ):
        raise ValueError(f"無効なHEX色コード: #{hex_color}")

    # RGB値に変換
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)

    # アルファ値を0-255の範囲にクランプ
    alpha = max(0, min(255, alpha))

    return (r, g, b, alpha)


def percent_to_alpha(percent: Union[int, float]) -> int:
    """
    パーセント値をアルファ値（0-255）に変換

    Args:
        percent: パーセント値（0-100）

    Returns:
        int: アルファ値（0-255）
    """
    # パーセント値を0-100の範囲にクランプ
    percent = max(0, min(100, float(percent)))

    # 0-255の範囲に変換
    return int((percent / 100.0) * 255)


def rgba_with_alpha_percent(
    hex_color: str, alpha_percent: Union[int, float]
) -> Tuple[int, int, int, int]:
    """
    HEX色コードとパーセント透過度からRGBA値を取得

    Args:
        hex_color: HEX色コード
        alpha_percent: 透過度（0-100%）

    Returns:
        Tuple[int, int, int, int]: RGBA値のタプル
    """
    alpha = percent_to_alpha(alpha_percent)
    return hex_to_rgba(hex_color, alpha)


def generate_output_filename(
    base_name: str, index: int, extension: str = "jpg"
) -> str:
    """
    出力ファイル名を生成（連番付き）

    Args:
        base_name: ベースとなる作品名
        index: 連番（1から開始）
        extension: ファイル拡張子（デフォルト: "jpg"）

    Returns:
        str: 生成されたファイル名（例: "作品名_001.jpg"）
    """
    # 拡張子からドットを除去
    extension = extension.lstrip(".")

    # 3桁ゼロパディングで連番を作成
    padded_index = f"{index:03d}"

    return f"{base_name}_{padded_index}.{extension}"


def sanitize_filename(filename: str) -> str:
    """
    ファイル名として使用できない文字を安全な文字に置換

    Args:
        filename: 元のファイル名

    Returns:
        str: サニタイズされたファイル名
    """
    # Windowsで使用できない文字を置換
    invalid_chars = r'[<>:"/\\|?*]'
    sanitized = re.sub(invalid_chars, "_", filename)

    # 連続するアンダースコアを一つにまとめる
    sanitized = re.sub(r"_+", "_", sanitized)

    # 先頭末尾のアンダースコアとスペースを除去
    sanitized = sanitized.strip("_ ")

    # 空文字列の場合はデフォルト名を使用
    if not sanitized:
        sanitized = "untitled"

    return sanitized


def extract_scene_number(scene_tag: str) -> Optional[str]:
    """
    [scene:XXX]タグから番号部分を抽出

    Args:
        scene_tag: sceneタグ文字列（例: "[scene:001]"）

    Returns:
        Optional[str]: 抽出された番号（例: "001"）、見つからない場合はNone
    """
    pattern = r"\[scene:([^\]]+)\]"
    match = re.search(pattern, scene_tag, re.IGNORECASE)

    if match:
        return match.group(1)
    return None


def validate_image_path(
    image_folder: Union[str, Path], scene_number: str
) -> Optional[Path]:
    """
    指定されたシーン番号の画像ファイルが存在するかチェック

    Args:
        image_folder: 画像フォルダのパス
        scene_number: シーン番号（例: "001"）

    Returns:
        Optional[Path]: 見つかった画像ファイルのパス、見つからない場合はNone
    """
    image_folder = Path(image_folder)

    if not image_folder.exists() or not image_folder.is_dir():
        return None

    # よくある画像拡張子をチェック
    extensions = [".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tiff"]

    for ext in extensions:
        image_path = image_folder / f"{scene_number}{ext}"
        if image_path.exists():
            return image_path

    return None


def parse_serif_text(text: str) -> list:
    """
    テキストからセリフ（「」で囲まれた部分）を抽出

    Args:
        text: 解析するテキスト

    Returns:
        list: 抽出されたセリフのリスト
    """
    # 「」で囲まれた部分を抽出
    pattern = r"「([^」]*)」"
    matches = re.findall(pattern, text)

    # 空白のみのセリフを除外
    serifs = [serif.strip() for serif in matches if serif.strip()]

    return serifs


def is_empty_line(line: str) -> bool:
    """
    行が空行（空白文字のみ）かどうかをチェック

    Args:
        line: チェックする行

    Returns:
        bool: 空行の場合True
    """
    return not line.strip()


def calculate_text_dimensions(
    text: str, font_size: int, max_chars_per_line: int
) -> Tuple[int, int]:
    """
    テキストの描画に必要な概算サイズを計算

    Args:
        text: 描画するテキスト
        font_size: フォントサイズ
        max_chars_per_line: 1行あたりの最大文字数

    Returns:
        Tuple[int, int]: (幅, 高さ) の概算ピクセル数
    """
    import textwrap

    # テキストを指定文字数で折り返し
    wrapped_lines = textwrap.wrap(text, width=max_chars_per_line)

    if not wrapped_lines:
        return (0, 0)

    # 各行の最大文字数を取得
    max_line_length = max(len(line) for line in wrapped_lines)
    line_count = len(wrapped_lines)

    # 概算サイズを計算（日本語フォントの場合、幅≒高さと仮定）
    estimated_width = max_line_length * font_size
    estimated_height = line_count * font_size * 1.2  # 行間を考慮

    return (int(estimated_width), int(estimated_height))


def clamp_value(
    value: Union[int, float],
    min_val: Union[int, float],
    max_val: Union[int, float],
) -> Union[int, float]:
    """
    値を指定された範囲内にクランプ

    Args:
        value: クランプする値
        min_val: 最小値
        max_val: 最大値

    Returns:
        Union[int, float]: クランプされた値
    """
    return max(min_val, min(max_val, value))


def safe_int_conversion(value: Union[str, int, float], default: int = 0) -> int:
    """
    値を安全に整数に変換

    Args:
        value: 変換する値
        default: 変換失敗時のデフォルト値

    Returns:
        int: 変換された整数値
    """
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return default


def format_error_message(error: Exception, context: str = "") -> str:
    """
    エラーメッセージを整形

    Args:
        error: 例外オブジェクト
        context: エラーの文脈情報

    Returns:
        str: 整形されたエラーメッセージ
    """
    error_type = type(error).__name__
    error_message = str(error)

    if context:
        return f"[{context}] {error_type}: {error_message}"
    else:
        return f"{error_type}: {error_message}"


def get_text_alignment_offset(
    text_width: int, container_width: int, alignment: str
) -> int:
    """
    テキストの配置に応じたオフセットを計算

    Args:
        text_width: テキストの幅
        container_width: コンテナの幅
        alignment: 配置方法（"left", "center", "right"）

    Returns:
        int: X座標のオフセット
    """
    alignment = alignment.lower()

    if alignment == "center":
        return (container_width - text_width) // 2
    elif alignment == "right":
        return container_width - text_width
    else:  # "left" または不明な値
        return 0


# 定数定義
class Constants:
    """アプリケーション全体で使用する定数"""

    # デフォルト画像サイズ
    DEFAULT_WIDTH = 960
    DEFAULT_HEIGHT = 1280

    # デフォルトフォントサイズ
    DEFAULT_FONT_SIZE = 48

    # セリフの最大数（1シーンあたり）
    MAX_SERIFS_PER_SCENE = 2

    # サポートする画像拡張子
    SUPPORTED_IMAGE_EXTENSIONS = [
        ".png",
        ".jpg",
        ".jpeg",
        ".bmp",
        ".gif",
        ".tiff",
    ]

    # サポートする出力形式
    SUPPORTED_OUTPUT_FORMATS = ["jpg", "png"]

    # デフォルト色
    DEFAULT_TEXT_COLOR = "#000000"
    DEFAULT_SERIF_COLOR = "#2A2A2A"
    DEFAULT_SERIF_BG_COLOR = "#FFFFFF"
    DEFAULT_SERIF_BORDER_COLOR = "#3C4C6A"
    DEFAULT_NARRATION_BG_COLOR = "#003232"


if __name__ == "__main__":
    # テスト用コード
    print("=== core/utils.py テスト ===")

    # HEX色変換テスト
    print("HEX色変換テスト:")
    test_colors = ["#FF0000", "#00FF00", "#0000FF", "RGB", "FFF"]
    for color in test_colors:
        try:
            rgba = hex_to_rgba(color)
            print(f"  {color} -> {rgba}")
        except ValueError as e:
            print(f"  {color} -> エラー: {e}")

    # ファイル名生成テスト
    print("\nファイル名生成テスト:")
    for i in range(1, 4):
        filename = generate_output_filename("テスト作品", i)
        print(f"  {i} -> {filename}")

    # セリフ抽出テスト
    print("\nセリフ抽出テスト:")
    test_text = "彼は言った。「こんにちは」そして彼女は答えた。「こんばんは」"
    serifs = parse_serif_text(test_text)
    print(f"  テキスト: {test_text}")
    print(f"  セリフ: {serifs}")

    print("\nテスト完了")
