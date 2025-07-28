#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小説画像化ツール - テキスト解析モジュール
小説テキストの解析、scene/para/セリフ検出、出力用データ構造への変換
"""

import re
from typing import List, Dict, Optional, Union, Tuple
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

from .utils import (
    extract_scene_number,
    parse_serif_text,
    is_empty_line,
    Constants,
)


class BlockType(Enum):
    """ブロックの種類を定義"""

    SCENE_ONLY = "scene_only"  # 画像のみ（文字なし）
    SCENE_WITH_SERIFS = "scene_with_serifs"  # 画像＋セリフ
    NARRATION = "narration"  # ナレーション（地の文）
    PAGE_BREAK = "page_break"  # 改ページ


@dataclass
class SerifData:
    """セリフデータの構造"""

    text: str  # セリフの内容
    position: str  # 配置位置（"top_right", "bottom_left"）
    order: int  # 順序（1番目、2番目）


@dataclass
class SceneBlock:
    """シーンブロックのデータ構造"""

    block_type: BlockType  # ブロックの種類
    scene_number: Optional[str]  # シーン番号（例: "001"）
    serifs: List[SerifData]  # セリフリスト（最大2個）
    narration_text: str  # ナレーションテキスト
    is_empty_after_scene: bool  # scene行の直後が空行か
    raw_lines: List[str]  # 元の行データ（デバッグ用）


class NovelTextParser:
    """小説テキストの解析を行うクラス"""

    def __init__(self):
        self.scene_pattern = re.compile(r"\[scene:([^\]]+)\]", re.IGNORECASE)
        self.para_pattern = re.compile(r"\[para\]", re.IGNORECASE)
        self.serif_pattern = re.compile(r"「([^」]*)」")

    def parse_file(self, text_file_path: Union[str, Path]) -> List[SceneBlock]:
        """
        テキストファイルを解析してSceneBlockのリストを返す

        Args:
            text_file_path: 小説テキストファイルのパス

        Returns:
            List[SceneBlock]: 解析されたブロックのリスト

        Raises:
            FileNotFoundError: ファイルが見つからない場合
            UnicodeDecodeError: ファイルの文字エンコーディングが不正な場合
        """
        text_file_path = Path(text_file_path)

        if not text_file_path.exists():
            raise FileNotFoundError(f"テキストファイルが見つかりません: {text_file_path}")

        try:
            with open(text_file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except UnicodeDecodeError:
            # UTF-8で読めない場合はShift_JISを試す
            try:
                with open(text_file_path, "r", encoding="shift_jis") as f:
                    lines = f.readlines()
            except UnicodeDecodeError:
                raise UnicodeDecodeError(
                    f"ファイルの文字エンコーディングが不正です: {text_file_path}\n"
                    "UTF-8またはShift_JISでエンコードされたファイルを使用してください。"
                )

        # 行末の改行文字を除去
        lines = [line.rstrip("\n\r") for line in lines]

        return self.parse_lines(lines)

    def parse_lines(self, lines: List[str]) -> List[SceneBlock]:
        """
        行のリストを解析してSceneBlockのリストを返す

        Args:
            lines: テキストの行リスト

        Returns:
            List[SceneBlock]: 解析されたブロックのリスト
        """
        blocks = []
        current_block = None
        last_scene_number = None  # 最後に使用されたシーン番号を追跡
        i = 0

        while i < len(lines):
            line = lines[i].strip()

            # [scene:XXX] の処理
            if self.scene_pattern.match(line):
                # 前のブロックがあれば追加
                if current_block is not None:
                    blocks.append(current_block)

                # 新しいシーンブロックを開始
                scene_number = extract_scene_number(line)
                last_scene_number = scene_number  # シーン番号を記録
                current_block = SceneBlock(
                    block_type=BlockType.SCENE_ONLY,  # 初期値、後で変更される可能性
                    scene_number=scene_number,
                    serifs=[],
                    narration_text="",
                    is_empty_after_scene=False,
                    raw_lines=[line],
                )

                # 次の行が空行かチェック
                if i + 1 < len(lines) and is_empty_line(lines[i + 1]):
                    current_block.is_empty_after_scene = True
                    i += 1  # 空行をスキップ
                    current_block.raw_lines.append(lines[i])

                i += 1
                continue

            # [para] の処理
            elif self.para_pattern.match(line):
                # 前のブロックがあれば追加
                if current_block is not None:
                    blocks.append(current_block)

                # 改ページブロックを追加
                para_block = SceneBlock(
                    block_type=BlockType.PAGE_BREAK,
                    scene_number=None,
                    serifs=[],
                    narration_text="",
                    is_empty_after_scene=False,
                    raw_lines=[line],
                )
                blocks.append(para_block)
                current_block = None
                # [para]後もシーン番号は継続（リセットしない）

                i += 1
                continue

            # 空行の処理
            elif is_empty_line(line):
                if current_block is not None:
                    current_block.raw_lines.append(line)
                i += 1
                continue

            # テキスト行の処理
            else:
                if current_block is None:
                    # シーンブロックが開始されていない場合はナレーションブロックを作成
                    current_block = SceneBlock(
                        block_type=BlockType.NARRATION,
                        scene_number=None,  # 後でcurrent_scene_numberが割り当てられる
                        serifs=[],
                        narration_text="",
                        is_empty_after_scene=False,
                        raw_lines=[],
                    )

                current_block.raw_lines.append(line)

                # セリフかナレーションかを判定
                serifs = parse_serif_text(line)

                if serifs:
                    # セリフが見つかった場合
                    self._add_serifs_to_block(current_block, serifs)
                    # セリフがある場合はブロックタイプを更新
                    if current_block.scene_number is not None:
                        # シーン番号がある場合
                        if (
                            current_block.block_type == BlockType.NARRATION
                            and not current_block.narration_text.strip()
                        ):
                            current_block.block_type = (
                                BlockType.SCENE_WITH_SERIFS
                            )
                    else:
                        # シーン番号がない場合でもセリフブロックとして扱う
                        current_block.block_type = BlockType.SCENE_WITH_SERIFS
                else:
                    # ナレーションの場合
                    if current_block.narration_text:
                        current_block.narration_text += "\n"
                    current_block.narration_text += line

                i += 1
                continue

        # 最後のブロックを追加
        if current_block is not None:
            blocks.append(current_block)

        # ブロックタイプを最終決定
        self._finalize_block_types(blocks)

        return blocks

    def _add_serifs_to_block(self, block: SceneBlock, serifs: List[str]):
        """
        ブロックにセリフを追加（最大2個まで）

        Args:
            block: 対象のSceneBlock
            serifs: 追加するセリフのリスト
        """
        for serif_text in serifs:
            if len(block.serifs) >= Constants.MAX_SERIFS_PER_SCENE:
                break

            # セリフの配置位置を決定
            position = "top_right" if len(block.serifs) == 0 else "bottom_left"
            order = len(block.serifs) + 1

            serif_data = SerifData(
                text=serif_text, position=position, order=order
            )

            block.serifs.append(serif_data)

    def _finalize_block_types(self, blocks: List[SceneBlock]):
        """
        ブロックタイプを最終決定する

        Args:
            blocks: SceneBlockのリスト
        """
        for block in blocks:
            if block.block_type == BlockType.PAGE_BREAK:
                continue

            # scene番号があるブロックの処理
            if block.scene_number is not None:
                if (
                    block.is_empty_after_scene
                    and not block.serifs
                    and not block.narration_text.strip()
                ):
                    # scene直後が空行で、セリフもナレーションもない場合は画像のみ
                    block.block_type = BlockType.SCENE_ONLY
                elif block.serifs:
                    # セリフがある場合
                    block.block_type = BlockType.SCENE_WITH_SERIFS
                else:
                    # ナレーションがある場合
                    block.block_type = BlockType.NARRATION
            else:
                # scene番号がない場合
                if block.serifs:
                    # セリフがある場合はセリフブロック
                    block.block_type = BlockType.SCENE_WITH_SERIFS
                else:
                    # ナレーションブロック
                    block.block_type = BlockType.NARRATION

    def generate_output_blocks(self, blocks: List[SceneBlock]) -> List[Dict]:
        """
        SceneBlockリストを出力用の辞書リストに変換

        Args:
            blocks: SceneBlockのリスト

        Returns:
            List[Dict]: 出力用データの辞書リスト
        """
        output_blocks = []
        current_scene_number = None  # 現在のシーン番号を追跡

        for block in blocks:
            if block.block_type == BlockType.PAGE_BREAK:
                continue

            # シーン番号の更新: 新しいシーン番号があれば更新
            if block.scene_number is not None:
                current_scene_number = block.scene_number

            if block.block_type == BlockType.SCENE_ONLY:
                # 画像のみの場合
                output_blocks.append(
                    {
                        "type": "image_only",
                        "scene_number": current_scene_number,
                        "serifs": [],
                        "narration": "",
                    }
                )

            elif block.block_type == BlockType.SCENE_WITH_SERIFS:
                # 画像+セリフの場合
                serif_list = []
                for serif in block.serifs:
                    serif_list.append(
                        {
                            "text": serif.text,
                            "position": serif.position,
                            "order": serif.order,
                        }
                    )

                output_blocks.append(
                    {
                        "type": "image_with_serifs",
                        "scene_number": current_scene_number,
                        "serifs": serif_list,
                        "narration": "",
                    }
                )

                # ナレーションがある場合は同じシーン番号で別のブロックとして追加
                if block.narration_text.strip():
                    output_blocks.append(
                        {
                            "type": "narration",
                            "scene_number": current_scene_number,
                            "serifs": [],
                            "narration": block.narration_text.strip(),
                        }
                    )

            elif block.block_type == BlockType.NARRATION:
                # ナレーションの場合（現在のシーン番号を使用）
                output_blocks.append(
                    {
                        "type": "narration",
                        "scene_number": current_scene_number,
                        "serifs": [],
                        "narration": block.narration_text.strip(),
                    }
                )

        return output_blocks

    def validate_text_structure(self, blocks: List[SceneBlock]) -> List[str]:
        """
        テキスト構造の妥当性をチェックし、警告リストを返す

        Args:
            blocks: SceneBlockのリスト

        Returns:
            List[str]: 警告メッセージのリスト
        """
        warnings = []
        scene_numbers = set()

        for i, block in enumerate(blocks):
            # 重複するシーン番号のチェック
            if block.scene_number is not None:
                if block.scene_number in scene_numbers:
                    warnings.append(f"シーン番号 '{block.scene_number}' が重複しています")
                else:
                    scene_numbers.add(block.scene_number)

            # セリフ数のチェック
            if len(block.serifs) > Constants.MAX_SERIFS_PER_SCENE:
                warnings.append(
                    f"ブロック {i+1}: セリフが{Constants.MAX_SERIFS_PER_SCENE}個を超えています "
                    f"({len(block.serifs)}個)"
                )

            # 空のセリフのチェック
            for serif in block.serifs:
                if not serif.text.strip():
                    warnings.append(f"ブロック {i+1}: 空のセリフがあります")

        return warnings


def parse_novel_text(
    text_file_path: Union[str, Path]
) -> Tuple[List[Dict], List[str]]:
    """
    小説テキストファイルを解析する便利関数

    Args:
        text_file_path: テキストファイルのパス

    Returns:
        Tuple[List[Dict], List[str]]: (出力用ブロックリスト, 警告メッセージリスト)

    Raises:
        FileNotFoundError: ファイルが見つからない場合
        UnicodeDecodeError: 文字エンコーディングエラーの場合
    """
    parser = NovelTextParser()

    # テキストファイルを解析
    blocks = parser.parse_file(text_file_path)

    # 妥当性チェック
    warnings = parser.validate_text_structure(blocks)

    # 出力用データに変換
    output_blocks = parser.generate_output_blocks(blocks)

    return output_blocks, warnings


if __name__ == "__main__":
    # テスト用コード
    print("=== core/parser.py テスト ===")

    # サンプルテキストでテスト
    sample_text = """[scene:001]

「ずっと待ってたんだから……」
「私も直人君のこと、ちっちゃい頃から好きだったよ」
[para]
そう言って、彼女は涙ぐんだ

[scene:002]
[para]
彼女は目を細めて、何かを噛みしめるように微笑んだ。

[scene:003]

"""

    # 行に分割
    lines = sample_text.strip().split("\n")

    # パーサーでテスト
    parser = NovelTextParser()
    blocks = parser.parse_lines(lines)

    print(f"解析されたブロック数: {len(blocks)}")

    for i, block in enumerate(blocks):
        print(f"\nブロック {i+1}:")
        print(f"  タイプ: {block.block_type}")
        print(f"  シーン番号: {block.scene_number}")
        print(f"  セリフ数: {len(block.serifs)}")
        for j, serif in enumerate(block.serifs):
            print(f"    セリフ{j+1}: '{serif.text}' ({serif.position})")
        if block.narration_text:
            print(f"  ナレーション: '{block.narration_text}'")

    # 出力用データに変換
    output_blocks = parser.generate_output_blocks(blocks)
    print(f"\n出力用ブロック数: {len(output_blocks)}")

    for i, output_block in enumerate(output_blocks):
        print(f"出力ブロック {i+1}: {output_block}")

    print("\nテスト完了")
