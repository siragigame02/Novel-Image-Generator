#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小説画像化ツール - 画像描画モジュール
背景画像の読み込み、テキスト描画、吹き出し描画、画像保存
"""

import os
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Union
from PIL import Image, ImageDraw, ImageFont
import traceback

from .utils import (
    ensure_directory_exists,
    hex_to_rgba,
    rgba_with_alpha_percent,
    validate_image_path,
    generate_output_filename,
    sanitize_filename,
    format_error_message,
    Constants,
)
from .layout import (
    TextLayoutCalculator,
    BubbleLayout,
    NarrationLayout,
    TextOrientation,
)


class ImageRenderer:
    """画像描画を行うクラス"""

    def __init__(
        self,
        output_width: int = Constants.DEFAULT_WIDTH,
        output_height: int = Constants.DEFAULT_HEIGHT,
    ):
        self.output_width = output_width
        self.output_height = output_height
        self.layout_calculator = TextLayoutCalculator(
            output_width, output_height
        )

        # デフォルトフォント設定
        self.default_font_size = Constants.DEFAULT_FONT_SIZE
        self.default_font_path = None
        self.loaded_fonts = {}  # フォントキャッシュ

    def load_font(
        self, font_path: Optional[str], font_size: int
    ) -> ImageFont.ImageFont:
        """
        フォントを読み込み（キャッシュ機能付き）

        Args:
            font_path: フォントファイルのパス（Noneの場合はデフォルトフォント）
            font_size: フォントサイズ

        Returns:
            ImageFont.ImageFont: 読み込まれたフォント
        """
        cache_key = (font_path or "default", font_size)

        if cache_key in self.loaded_fonts:
            return self.loaded_fonts[cache_key]

        try:
            if font_path and Path(font_path).exists():
                font = ImageFont.truetype(font_path, font_size)
            else:
                # デフォルトフォントを使用
                try:
                    # Windows環境の場合
                    default_paths = [
                        "C:/Windows/Fonts/meiryo.ttc",
                        "C:/Windows/Fonts/yugothm.ttc",
                        "C:/Windows/Fonts/msmincho.ttc",
                    ]
                    font = None
                    for path in default_paths:
                        if Path(path).exists():
                            font = ImageFont.truetype(path, font_size)
                            break

                    if font is None:
                        font = ImageFont.load_default()
                        print(f"警告: デフォルトフォントを使用します（サイズ調整不可）")

                except Exception:
                    font = ImageFont.load_default()
                    print(f"警告: デフォルトフォントを使用します")
            self.loaded_fonts[cache_key] = font
            return font

        except Exception as e:
            print(f"フォント読み込みエラー: {e}")
            font = self._load_default_font(font_size)
            self.loaded_fonts[cache_key] = font
            return font

    def _load_default_font(self, font_size: int) -> ImageFont.ImageFont:
        """
        デフォルトフォントを読み込み

        Args:
            font_size: フォントサイズ

        Returns:
            ImageFont.ImageFont: デフォルトフォント
        """
        try:
            # Windows環境の場合（ttf/ttc両対応）
            default_paths = [
                "C:/Windows/Fonts/meiryo.ttc",
                "C:/Windows/Fonts/yugothm.ttc",
                "C:/Windows/Fonts/msmincho.ttc",
                "C:/Windows/Fonts/meiryo.ttf",
                "C:/Windows/Fonts/yugothm.ttf",
                "C:/Windows/Fonts/msmincho.ttf",
                "C:/Windows/Fonts/NotoSansCJK-Regular.ttc",
                "C:/Windows/Fonts/NotoSansCJK.ttc",
                # macOS環境
                "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
                "/System/Library/Fonts/Hiragino Sans GB.ttc",
                "/System/Library/Fonts/PingFang.ttc",
                # Linux環境
                "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
                "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.otf",
            ]

            for path in default_paths:
                if Path(path).exists():
                    return ImageFont.truetype(path, font_size)

            # すべて見つからない場合はPillowのデフォルトフォント
            print(f"警告: 日本語対応フォントが見つかりません。デフォルトフォントを使用します（サイズ調整不可）")
            return ImageFont.load_default()

        except Exception as e:
            print(f"デフォルトフォント読み込みエラー: {e}")
            return ImageFont.load_default()

    def create_base_image(
        self, background_path: Optional[str] = None
    ) -> Image.Image:
        """
        ベース画像を作成（背景画像または無地背景）

        Args:
            background_path: 背景画像のパス（Noneの場合は白背景）

        Returns:
            Image.Image: 作成されたベース画像
        """
        if background_path and Path(background_path).exists():
            try:
                # 背景画像を読み込み
                bg_image = Image.open(background_path)

                # RGBA形式に変換
                if bg_image.mode != "RGBA":
                    bg_image = bg_image.convert("RGBA")

                # 指定サイズにリサイズ
                bg_image = bg_image.resize(
                    (self.output_width, self.output_height),
                    Image.Resampling.LANCZOS,
                )

                return bg_image

            except Exception as e:
                print(f"背景画像読み込みエラー: {e}")
                print("白背景を使用します")

        # 白背景を作成
        return Image.new(
            "RGBA",
            (self.output_width, self.output_height),
            (255, 255, 255, 255),
        )

    def draw_narration_background(
        self,
        image: Image.Image,
        layout: NarrationLayout,
        bg_color: str,
        bg_alpha: int,
    ) -> Image.Image:
        """
        ナレーション用の半透明背景を描画

        Args:
            image: ベース画像
            layout: ナレーションレイアウト
            bg_color: 背景色（HEX）
            bg_alpha: 透過度（0-100%）

        Returns:
            Image.Image: 背景が描画された画像
        """
        try:
            # 半透明レイヤーを作成
            overlay = Image.new(
                "RGBA", (self.output_width, self.output_height), (0, 0, 0, 0)
            )
            overlay_draw = ImageDraw.Draw(overlay)

            # 背景色をRGBAに変換
            bg_rgba = rgba_with_alpha_percent(bg_color, bg_alpha)

            # 背景矩形を描画
            overlay_draw.rectangle(
                [
                    layout.bg_x,
                    layout.bg_y,
                    layout.bg_x + layout.bg_width,
                    layout.bg_y + layout.bg_height,
                ],
                fill=bg_rgba,
            )

            # ベース画像と合成
            result = Image.alpha_composite(image, overlay)
            return result

        except Exception as e:
            print(f"ナレーション背景描画エラー: {e}")
            return image

    def draw_bubble_background(
        self,
        image: Image.Image,
        layout: BubbleLayout,
        bg_color: str,
        bg_alpha: int,
        border_color: str,
    ) -> Image.Image:
        """
        セリフ吹き出しの背景を描画

        Args:
            image: ベース画像
            layout: 吹き出しレイアウト
            bg_color: 背景色（HEX）
            bg_alpha: 透過度（0-100%）
            border_color: 枠線色（HEX）

        Returns:
            Image.Image: 吹き出しが描画された画像
        """
        try:
            draw = ImageDraw.Draw(image)

            # 背景色と枠線色をRGBAに変換
            bg_rgba = rgba_with_alpha_percent(bg_color, bg_alpha)
            border_rgba = hex_to_rgba(border_color, 255)

            # 角丸矩形の座標
            x1, y1 = layout.bubble_x, layout.bubble_y
            x2, y2 = (
                layout.bubble_x + layout.bubble_width,
                layout.bubble_y + layout.bubble_height,
            )

            # 角丸矩形を描画（背景）
            self._draw_rounded_rectangle(
                draw, [x1, y1, x2, y2], radius=15, fill=bg_rgba, outline=None
            )

            # 角丸矩形を描画（枠線）
            self._draw_rounded_rectangle(
                draw,
                [x1, y1, x2, y2],
                radius=15,
                fill=None,
                outline=border_rgba,
                width=2,
            )

            return image

        except Exception as e:
            print(f"吹き出し描画エラー: {e}")
            return image

    def _draw_rounded_rectangle(
        self,
        draw: ImageDraw.ImageDraw,
        coords: List[int],
        radius: int,
        fill=None,
        outline=None,
        width: int = 1,
    ):
        """
        角丸矩形を描画

        Args:
            draw: ImageDrawオブジェクト
            coords: [x1, y1, x2, y2] 座標
            radius: 角の半径
            fill: 塗りつぶし色
            outline: 枠線色
            width: 枠線の太さ
        """
        x1, y1, x2, y2 = coords

        # Pillowの角丸矩形機能を使用（Pillow 8.2.0以降）
        try:
            if fill is not None:
                draw.rounded_rectangle(
                    [x1, y1, x2, y2], radius=radius, fill=fill
                )
            if outline is not None:
                draw.rounded_rectangle(
                    [x1, y1, x2, y2],
                    radius=radius,
                    outline=outline,
                    width=width,
                )
        except AttributeError:
            # 古いPillowの場合は通常の矩形で代用
            if fill is not None:
                draw.rectangle([x1, y1, x2, y2], fill=fill)
            if outline is not None:
                draw.rectangle([x1, y1, x2, y2], outline=outline, width=width)

    def draw_text_vertical(
        self,
        image: Image.Image,
        layout: BubbleLayout,
        font: ImageFont.ImageFont,
        text_color: str,
    ) -> Image.Image:
        """
        縦書きテキストを描画

        Args:
            image: ベース画像
            layout: テキストレイアウト
            font: フォント
            text_color: テキスト色（HEX）

        Returns:
            Image.Image: テキストが描画された画像
        """
        try:
            draw = ImageDraw.Draw(image)
            text_rgba = hex_to_rgba(text_color, 255)

            # 文字位置を計算
            positions = self.layout_calculator.get_text_character_positions(
                layout
            )

            # 各文字を描画
            for x, y, char in positions:
                # 縦書き用の文字変換
                converted_char = self._convert_char_for_vertical(char)
                draw.text((x, y), converted_char, font=font, fill=text_rgba)

            return image

        except Exception as e:
            print(f"縦書きテキスト描画エラー: {e}")
            return image

    def _convert_char_for_vertical(self, char: str) -> str:
        """
        縦書き用に文字を変換（フォント対応を考慮した安全な変換）

        Args:
            char: 変換する文字

        Returns:
            str: 変換された文字
        """
        # 縦書き用文字変換テーブル（段階的に適用）

        # 確実に変換すべきもの（長音符）
        essential_conversion = {
            "ー": "｜",
            "−": "｜",
            "―": "｜",
            "─": "｜",
        }

        # 一般的なフォントで対応されているもの
        safe_conversion = {
            "…": "︙",
            "⋯": "︙",
            "〜": "︴",
            "～": "︴",
        }

        # 括弧類（比較的安全）
        # bracket_conversion = {
        #    "（": "︵",
        #    "）": "︶",
        #    "(": "︵",
        #    ")": "︶",
        #    "「": "﹁",
        #    "」": "﹂",
        #    "『": "﹃",
        #    "』": "﹄",
        # }

        # まず確実なものから変換
        if char in essential_conversion:
            return essential_conversion[char]

        # 次に安全なものを変換
        if char in safe_conversion:
            return safe_conversion[char]

        # 括弧類を変換（オプション・問題があればコメントアウト可能）
        # if char in bracket_conversion:
        #    return bracket_conversion[char]

        # その他はそのまま返す（句読点、感嘆符、疑問符など）
        return char

    def draw_text_horizontal(
        self,
        image: Image.Image,
        layout: NarrationLayout,
        font: ImageFont.ImageFont,
        text_color: str,
    ) -> Image.Image:
        """
        横書きテキストを描画

        Args:
            image: ベース画像
            layout: テキストレイアウト
            font: フォント
            text_color: テキスト色（HEX）

        Returns:
            Image.Image: テキストが描画された画像
        """
        try:
            draw = ImageDraw.Draw(image)
            text_rgba = hex_to_rgba(text_color, 255)

            # 行ごとに描画
            current_y = layout.text_y
            for line in layout.text_block.lines:
                if line.strip():  # 空行でない場合
                    # 行の配置を計算
                    if layout.alignment.value == "center":
                        line_width = len(line) * layout.text_block.char_width
                        line_x = (
                            layout.text_x
                            + (layout.bg_width - line_width) // 2
                            - layout.text_x
                        )
                        line_x = max(layout.text_x, line_x)
                    elif layout.alignment.value == "right":
                        line_width = len(line) * layout.text_block.char_width
                        line_x = (
                            layout.bg_x + layout.bg_width - line_width - 30
                        )  # padding
                    else:  # left
                        line_x = layout.text_x

                    draw.text(
                        (line_x, current_y), line, font=font, fill=text_rgba
                    )

                current_y += layout.text_block.line_height

            return image

        except Exception as e:
            print(f"横書きテキスト描画エラー: {e}")
            return image

    def render_image_only(
        self,
        scene_number: str,
        image_folder: str,
        output_folder: str,
        base_name: str,
        index: int,
    ) -> bool:
        """
        画像のみを出力（テキストなし）

        Args:
            scene_number: シーン番号
            image_folder: 画像フォルダのパス
            output_folder: 出力フォルダのパス
            base_name: 出力ファイルのベース名
            index: 出力ファイルの連番

        Returns:
            bool: 成功時True
        """
        try:
            # 背景画像パスを取得
            bg_path = validate_image_path(image_folder, scene_number)
            if bg_path is None:
                print(f"エラー: シーン {scene_number} の画像が見つかりません")
                return False

            # 画像を作成
            image = self.create_base_image(str(bg_path))

            # RGB形式に変換して保存
            rgb_image = self._convert_to_rgb(image)

            # 出力パスを生成
            output_path = self._generate_output_path(
                output_folder, base_name, index
            )

            # 画像を保存
            rgb_image.save(output_path, "JPEG", quality=95, optimize=True)
            print(f"画像のみ出力: {output_path}")

            return True

        except Exception as e:
            print(
                f"画像のみ出力エラー: {format_error_message(e, f'scene:{scene_number}')}"
            )
            return False

    def render_image_with_serifs(
        self,
        scene_number: str,
        serifs: List[Dict],
        image_folder: str,
        output_folder: str,
        base_name: str,
        index: int,
        settings: Dict,
    ) -> bool:
        """
        画像+セリフを出力

        Args:
            scene_number: シーン番号（Noneの場合は白背景）
            serifs: セリフリスト
            image_folder: 画像フォルダのパス
            output_folder: 出力フォルダのパス
            base_name: 出力ファイルのベース名
            index: 出力ファイルの連番
            settings: 描画設定

        Returns:
            bool: 成功時True
        """
        try:
            # 背景画像パスを取得
            bg_path = None
            if scene_number and image_folder:
                bg_path = validate_image_path(image_folder, scene_number)
                if bg_path is None:
                    print(f"警告: シーン {scene_number} の画像が見つかりません。白背景を使用します。")

            # ベース画像を作成
            image = self.create_base_image(str(bg_path) if bg_path else None)

            # フォントを読み込み
            font = self.load_font(
                settings.get("serif_font_path"), settings.get("font_size", 48)
            )

            # セリフ吹き出しを描画
            for serif in serifs:
                if not serif["text"].strip():
                    continue

                # レイアウト計算
                layout = self.layout_calculator.calculate_serif_bubble_layout(
                    serif["text"],
                    settings.get("font_size", 48),
                    settings.get("max_chars", 10),
                    serif["position"],
                )

                # 吹き出し背景を描画
                image = self.draw_bubble_background(
                    image,
                    layout,
                    settings.get("serif_bg_color", "#FFFFFF"),
                    settings.get("serif_bg_alpha", 30),
                    settings.get("serif_border_color", "#3C4C6A"),
                )

                # テキストを描画
                image = self.draw_text_vertical(
                    image,
                    layout,
                    font,
                    settings.get("serif_font_color", "#2A2A2A"),
                )

            # RGB形式に変換して保存
            rgb_image = self._convert_to_rgb(image)
            output_path = self._generate_output_path(
                output_folder, base_name, index
            )
            rgb_image.save(output_path, "JPEG", quality=95, optimize=True)
            print(f"セリフ付き画像出力: {output_path}")

            return True

        except Exception as e:
            print(
                f"セリフ付き画像出力エラー: {format_error_message(e, f'scene:{scene_number}')}"
            )
            return False

    def render_narration(
        self,
        narration_text: str,
        scene_number: Optional[str],
        image_folder: Optional[str],
        output_folder: str,
        base_name: str,
        index: int,
        settings: Dict,
    ) -> bool:
        """
        ナレーションを出力

        Args:
            narration_text: ナレーションテキスト
            scene_number: シーン番号（背景画像用、Noneの場合は前の背景を使用）
            image_folder: 画像フォルダのパス
            output_folder: 出力フォルダのパス
            base_name: 出力ファイルのベース名
            index: 出力ファイルの連番
            settings: 描画設定

        Returns:
            bool: 成功時True
        """
        try:
            # 背景画像を取得
            bg_path = None
            if scene_number and image_folder:
                bg_path = validate_image_path(image_folder, scene_number)

            # ベース画像を作成
            image = self.create_base_image(str(bg_path) if bg_path else None)

            # フォントを読み込み
            font = self.load_font(
                settings.get("font_path"), settings.get("font_size", 48)
            )

            # ナレーションレイアウト計算
            layout = self.layout_calculator.calculate_narration_layout(
                narration_text,
                settings.get("font_size", 48),
                settings.get("max_chars", 35),
                settings.get("narration_text_align", "center"),
                settings.get("narration_orientation", "horizontal"),
            )

            # ナレーション背景を描画
            image = self.draw_narration_background(
                image,
                layout,
                settings.get("narration_bg_color", "#003232"),
                settings.get("narration_bg_alpha", 30),
            )

            # テキストを描画
            image = self.draw_text_horizontal(
                image, layout, font, settings.get("font_color", "#FFFFFF")
            )

            # RGB形式に変換して保存
            rgb_image = self._convert_to_rgb(image)
            output_path = self._generate_output_path(
                output_folder, base_name, index
            )
            rgb_image.save(output_path, "JPEG", quality=95, optimize=True)
            print(f"ナレーション出力: {output_path}")

            return True

        except Exception as e:
            print(f"ナレーション出力エラー: {format_error_message(e, f'narration')}")
            return False

    def _convert_to_rgb(self, image: Image.Image) -> Image.Image:
        """
        RGBA画像をRGB画像に変換

        Args:
            image: RGBA画像

        Returns:
            Image.Image: RGB画像
        """
        if image.mode == "RGBA":
            # 白背景でアルファ合成
            rgb_image = Image.new("RGB", image.size, (255, 255, 255))
            rgb_image.paste(image, mask=image.split()[-1])  # アルファチャンネルをマスクとして使用
            return rgb_image
        elif image.mode != "RGB":
            return image.convert("RGB")
        else:
            return image

    def _generate_output_path(
        self, output_folder: str, base_name: str, index: int
    ) -> Path:
        """
        出力パスを生成

        Args:
            output_folder: 出力フォルダ
            base_name: ベース名
            index: 連番

        Returns:
            Path: 出力パス
        """
        output_dir = ensure_directory_exists(output_folder)
        filename = generate_output_filename(sanitize_filename(base_name), index)
        return output_dir / filename


def render_novel_blocks(
    blocks: List[Dict],
    image_folder: str,
    output_folder: str,
    base_name: str,
    settings: Dict,
) -> Tuple[bool, List[str]]:
    """
    小説ブロックリストを画像として出力する便利関数

    Args:
        blocks: 出力ブロックリスト
        image_folder: 画像フォルダのパス
        output_folder: 出力フォルダのパス
        base_name: 出力ファイルのベース名
        settings: 描画設定

    Returns:
        Tuple[bool, List[str]]: (成功フラグ, エラーメッセージリスト)
    """
    renderer = ImageRenderer(
        settings.get("output_width", Constants.DEFAULT_WIDTH),
        settings.get("output_height", Constants.DEFAULT_HEIGHT),
    )

    errors = []
    index = 1
    last_scene_number = None

    for block in blocks:
        try:
            block_type = block["type"]
            scene_number = block.get("scene_number")

            # シーン番号の管理: scene_numberがあれば更新、なければ前のものを継続
            if scene_number:
                last_scene_number = scene_number
            current_scene = scene_number if scene_number else last_scene_number

            if block_type == "image_only":
                success = renderer.render_image_only(
                    current_scene, image_folder, output_folder, base_name, index
                )

            elif block_type == "image_with_serifs":
                success = renderer.render_image_with_serifs(
                    current_scene,
                    block["serifs"],
                    image_folder,
                    output_folder,
                    base_name,
                    index,
                    settings,
                )

            elif block_type == "narration":
                # ナレーションでもシーン画像を背景として使用
                success = renderer.render_narration(
                    block["narration"],
                    current_scene,
                    image_folder,
                    output_folder,
                    base_name,
                    index,
                    settings,
                )

            else:
                errors.append(f"ブロック {index}: 不明なタイプ '{block_type}'")
                success = False

            if not success:
                errors.append(f"ブロック {index}: 出力に失敗しました")

            index += 1

        except Exception as e:
            error_msg = f"ブロック {index}: {format_error_message(e)}"
            errors.append(error_msg)
            print(error_msg)
            index += 1

    return len(errors) == 0, errors


if __name__ == "__main__":
    # テスト用コード
    print("=== core/renderer.py テスト ===")

    # レンダラーを作成
    renderer = ImageRenderer()

    # テスト用設定
    test_settings = {
        "font_size": 48,
        "serif_font_color": "#2A2A2A",
        "serif_bg_color": "#FFFFFF",
        "serif_bg_alpha": 30,
        "serif_border_color": "#3C4C6A",
        "narration_bg_color": "#003232",
        "narration_bg_alpha": 30,
        "font_color": "#FFFFFF",
        "max_chars": 35,
    }

    # ベース画像作成テスト
    print("ベース画像作成テスト:")
    base_image = renderer.create_base_image()
    print(f"  サイズ: {base_image.size}")
    print(f"  モード: {base_image.mode}")

    # フォント読み込みテスト
    print("\nフォント読み込みテスト:")
    font = renderer.load_font(None, 48)
    print(f"  フォント読み込み完了")

    print("\nテスト完了")
