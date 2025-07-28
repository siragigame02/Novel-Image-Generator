#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小説画像化ツール - テキストレイアウト計算モジュール
縦書き・横書きのテキスト配置、吹き出しサイズ計算、座標計算
"""

import textwrap
from typing import List, Tuple, Dict, Optional, Union
from dataclasses import dataclass
from enum import Enum

from .utils import (
    calculate_text_dimensions,
    get_text_alignment_offset,
    clamp_value,
    Constants,
)


class TextOrientation(Enum):
    """テキストの向き"""

    HORIZONTAL = "horizontal"  # 横書き
    VERTICAL = "vertical"  # 縦書き


class TextAlignment(Enum):
    """テキストの配置"""

    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"


@dataclass
class TextBlock:
    """テキストブロックの情報"""

    text: str  # 表示テキスト
    lines: List[str]  # 行分割されたテキスト
    width: int  # ブロックの幅
    height: int  # ブロックの高さ
    line_height: int  # 行の高さ
    char_width: int  # 文字幅
    orientation: TextOrientation  # テキストの向き


@dataclass
class BubbleLayout:
    """吹き出しのレイアウト情報"""

    text_block: TextBlock  # テキストブロック
    bubble_x: int  # 吹き出しのX座標
    bubble_y: int  # 吹き出しのY座標
    bubble_width: int  # 吹き出しの幅
    bubble_height: int  # 吹き出しの高さ
    text_x: int  # テキストのX座標
    text_y: int  # テキストのY座標
    padding: int  # 内側の余白


@dataclass
class NarrationLayout:
    """ナレーションのレイアウト情報"""

    text_block: TextBlock  # テキストブロック
    bg_x: int  # 背景のX座標
    bg_y: int  # 背景のY座標
    bg_width: int  # 背景の幅
    bg_height: int  # 背景の高さ
    text_x: int  # テキストのX座標
    text_y: int  # テキストのY座標
    alignment: TextAlignment  # テキストの配置


class TextLayoutCalculator:
    """テキストレイアウトの計算を行うクラス"""

    def __init__(
        self,
        canvas_width: int = Constants.DEFAULT_WIDTH,
        canvas_height: int = Constants.DEFAULT_HEIGHT,
    ):
        self.canvas_width = canvas_width
        self.canvas_height = canvas_height

        # 吹き出し設定
        self.bubble_padding = 20  # 吹き出し内の余白
        self.bubble_margin = 40  # 画面端からの余白
        self.bubble_corner_radius = 15  # 角の丸み

        # ナレーション設定
        self.narration_padding = 30  # ナレーション背景の余白
        self.narration_margin = 60  # 画面端からの余白

        # 行間設定
        self.line_spacing_ratio = 1.2  # 行間の比率

    def calculate_text_block(
        self,
        text: str,
        font_size: int,
        max_chars_per_line: int,
        orientation: TextOrientation = TextOrientation.VERTICAL,
    ) -> TextBlock:
        """
        テキストブロックの情報を計算

        Args:
            text: 表示するテキスト
            font_size: フォントサイズ
            max_chars_per_line: 1行あたりの最大文字数
            orientation: テキストの向き

        Returns:
            TextBlock: 計算されたテキストブロック情報
        """
        if not text.strip():
            return TextBlock(
                text="",
                lines=[],
                width=0,
                height=0,
                line_height=0,
                char_width=0,
                orientation=orientation,
            )

        # 行の高さと文字幅を計算（日本語フォントの場合、ほぼ正方形と仮定）
        line_height = int(font_size * self.line_spacing_ratio)
        char_width = font_size

        # テキストを行に分割
        lines = self._wrap_text(text, max_chars_per_line, orientation)

        if orientation == TextOrientation.VERTICAL:
            # 縦書きの場合
            block_width = len(lines) * char_width
            block_height = (
                max(len(line) for line in lines) * char_width if lines else 0
            )
        else:
            # 横書きの場合
            block_width = (
                max(len(line) for line in lines) * char_width if lines else 0
            )
            block_height = len(lines) * line_height

        return TextBlock(
            text=text,
            lines=lines,
            width=block_width,
            height=block_height,
            line_height=line_height,
            char_width=char_width,
            orientation=orientation,
        )

    def _wrap_text(
        self, text: str, max_chars_per_line: int, orientation: TextOrientation
    ) -> List[str]:
        """
        テキストを指定文字数で折り返し

        Args:
            text: 元のテキスト
            max_chars_per_line: 1行あたりの最大文字数
            orientation: テキストの向き

        Returns:
            List[str]: 行分割されたテキスト
        """
        # 改行で分割
        paragraphs = text.split("\n")
        all_lines = []

        for paragraph in paragraphs:
            if not paragraph.strip():
                all_lines.append("")
                continue

            # 指定文字数で折り返し
            wrapped = textwrap.wrap(
                paragraph, width=max_chars_per_line, break_long_words=True
            )
            if wrapped:
                all_lines.extend(wrapped)
            else:
                all_lines.append("")

        return all_lines

    def calculate_serif_bubble_layout(
        self, text: str, font_size: int, max_chars_per_line: int, position: str
    ) -> BubbleLayout:
        """
        セリフ吹き出しのレイアウトを計算

        Args:
            text: セリフテキスト
            font_size: フォントサイズ
            max_chars_per_line: 1行あたりの最大文字数
            position: 配置位置（"top_right" または "bottom_left"）

        Returns:
            BubbleLayout: 計算された吹き出しレイアウト
        """
        # テキストブロックを計算（縦書き）
        text_block = self.calculate_text_block(
            text, font_size, max_chars_per_line, TextOrientation.VERTICAL
        )

        # 吹き出しのサイズを計算
        bubble_width = text_block.width + (self.bubble_padding * 2)
        bubble_height = text_block.height + (self.bubble_padding * 2)

        # 配置位置に応じて座標を計算
        if position == "top_right":
            bubble_x = self.canvas_width - bubble_width - self.bubble_margin
            bubble_y = self.bubble_margin
        else:  # "bottom_left"
            bubble_x = self.bubble_margin
            bubble_y = self.canvas_height - bubble_height - self.bubble_margin

        # 画面内に収まるように調整
        bubble_x = clamp_value(
            bubble_x,
            self.bubble_margin,
            self.canvas_width - bubble_width - self.bubble_margin,
        )
        bubble_y = clamp_value(
            bubble_y,
            self.bubble_margin,
            self.canvas_height - bubble_height - self.bubble_margin,
        )

        # テキストの座標を計算
        text_x = bubble_x + self.bubble_padding
        text_y = bubble_y + self.bubble_padding

        return BubbleLayout(
            text_block=text_block,
            bubble_x=bubble_x,
            bubble_y=bubble_y,
            bubble_width=bubble_width,
            bubble_height=bubble_height,
            text_x=text_x,
            text_y=text_y,
            padding=self.bubble_padding,
        )

    def calculate_narration_layout(
        self,
        text: str,
        font_size: int,
        max_chars_per_line: int,
        alignment: str = "center",
        orientation: str = "horizontal",
    ) -> NarrationLayout:
        """
        ナレーションのレイアウトを計算

        Args:
            text: ナレーションテキスト
            font_size: フォントサイズ
            max_chars_per_line: 1行あたりの最大文字数
            alignment: テキストの配置（"left", "center", "right"）
            orientation: テキストの向き（"horizontal", "vertical"）

        Returns:
            NarrationLayout: 計算されたナレーションレイアウト
        """
        # テキストの向きを変換
        text_orientation = (
            TextOrientation.VERTICAL
            if orientation == "vertical"
            else TextOrientation.HORIZONTAL
        )

        # テキストブロックを計算
        text_block = self.calculate_text_block(
            text, font_size, max_chars_per_line, text_orientation
        )

        # 背景のサイズを計算
        bg_width = self.canvas_width - (self.narration_margin * 2)
        bg_height = text_block.height + (self.narration_padding * 2)

        # 背景の座標を計算（画面中央に配置）
        bg_x = self.narration_margin
        bg_y = (self.canvas_height - bg_height) // 2

        # テキストの配置を計算
        text_alignment = TextAlignment(alignment.lower())

        if text_alignment == TextAlignment.CENTER:
            text_x = bg_x + (bg_width - text_block.width) // 2
        elif text_alignment == TextAlignment.RIGHT:
            text_x = bg_x + bg_width - text_block.width - self.narration_padding
        else:  # LEFT
            text_x = bg_x + self.narration_padding

        text_y = bg_y + self.narration_padding

        # 画面内に収まるように調整
        text_x = clamp_value(
            text_x,
            bg_x + self.narration_padding,
            bg_x + bg_width - text_block.width - self.narration_padding,
        )

        return NarrationLayout(
            text_block=text_block,
            bg_x=bg_x,
            bg_y=bg_y,
            bg_width=bg_width,
            bg_height=bg_height,
            text_x=text_x,
            text_y=text_y,
            alignment=text_alignment,
        )

    def calculate_vertical_text_positions(
        self, text_block: TextBlock, start_x: int, start_y: int
    ) -> List[Tuple[int, int, str]]:
        """
        縦書きテキストの各文字の座標を計算（右から左に読む順序）

        Args:
            text_block: テキストブロック情報
            start_x: 開始X座標
            start_y: 開始Y座標

        Returns:
            List[Tuple[int, int, str]]: (x, y, 文字) のリスト
        """
        positions = []

        if text_block.orientation != TextOrientation.VERTICAL:
            return positions

        # 右から左に読む順序にするため、行を逆順で処理
        total_lines = len(text_block.lines)

        for line_index, line in enumerate(text_block.lines):
            # 右端から左に向かって配置（逆順インデックス）
            current_x = (
                start_x + (total_lines - 1 - line_index) * text_block.char_width
            )
            current_y = start_y

            for char in line:
                if char.strip():  # 空白文字以外
                    positions.append((current_x, current_y, char))
                current_y += text_block.char_width

        return positions

    def calculate_horizontal_text_positions(
        self, text_block: TextBlock, start_x: int, start_y: int
    ) -> List[Tuple[int, int, str]]:
        """
        横書きテキストの各文字の座標を計算

        Args:
            text_block: テキストブロック情報
            start_x: 開始X座標
            start_y: 開始Y座標

        Returns:
            List[Tuple[int, int, str]]: (x, y, 文字) のリスト
        """
        positions = []

        if text_block.orientation != TextOrientation.HORIZONTAL:
            return positions

        current_y = start_y

        for line in text_block.lines:
            current_x = start_x

            for char in line:
                if char.strip():  # 空白文字以外
                    positions.append((current_x, current_y, char))
                current_x += text_block.char_width

            current_y += text_block.line_height

        return positions

    def get_text_character_positions(
        self, layout: Union[BubbleLayout, NarrationLayout]
    ) -> List[Tuple[int, int, str]]:
        """
        レイアウトから文字位置のリストを取得

        Args:
            layout: BubbleLayoutまたはNarrationLayout

        Returns:
            List[Tuple[int, int, str]]: (x, y, 文字) のリスト
        """
        text_block = layout.text_block

        if text_block.orientation == TextOrientation.VERTICAL:
            return self.calculate_vertical_text_positions(
                text_block, layout.text_x, layout.text_y
            )
        else:
            return self.calculate_horizontal_text_positions(
                text_block, layout.text_x, layout.text_y
            )

    def adjust_bubble_positions(
        self, bubbles: List[BubbleLayout]
    ) -> List[BubbleLayout]:
        """
        複数の吹き出しが重ならないように位置を調整

        Args:
            bubbles: 吹き出しレイアウトのリスト

        Returns:
            List[BubbleLayout]: 調整された吹き出しレイアウトのリスト
        """
        if len(bubbles) <= 1:
            return bubbles

        adjusted_bubbles = []

        for i, bubble in enumerate(bubbles):
            adjusted_bubble = bubble

            # 他の吹き出しとの重複をチェック
            for existing_bubble in adjusted_bubbles:
                if self._bubbles_overlap(adjusted_bubble, existing_bubble):
                    # 重複している場合は位置を調整
                    adjusted_bubble = self._adjust_bubble_position(
                        adjusted_bubble, existing_bubble
                    )

            adjusted_bubbles.append(adjusted_bubble)

        return adjusted_bubbles

    def _bubbles_overlap(
        self, bubble1: BubbleLayout, bubble2: BubbleLayout
    ) -> bool:
        """
        2つの吹き出しが重複しているかチェック

        Args:
            bubble1: 吹き出し1
            bubble2: 吹き出し2

        Returns:
            bool: 重複している場合True
        """
        return not (
            bubble1.bubble_x + bubble1.bubble_width < bubble2.bubble_x
            or bubble2.bubble_x + bubble2.bubble_width < bubble1.bubble_x
            or bubble1.bubble_y + bubble1.bubble_height < bubble2.bubble_y
            or bubble2.bubble_y + bubble2.bubble_height < bubble1.bubble_y
        )

    def _adjust_bubble_position(
        self, bubble: BubbleLayout, existing_bubble: BubbleLayout
    ) -> BubbleLayout:
        """
        吹き出しの位置を調整して重複を回避

        Args:
            bubble: 調整する吹き出し
            existing_bubble: 既存の吹き出し

        Returns:
            BubbleLayout: 調整された吹き出し
        """
        # 簡単な調整：既存の吹き出しの下に移動
        new_y = existing_bubble.bubble_y + existing_bubble.bubble_height + 20

        # 画面内に収まるかチェック
        if (
            new_y + bubble.bubble_height
            > self.canvas_height - self.bubble_margin
        ):
            # 収まらない場合は上に移動
            new_y = existing_bubble.bubble_y - bubble.bubble_height - 20
            new_y = max(self.bubble_margin, new_y)

        # 新しいレイアウトを作成
        new_bubble = BubbleLayout(
            text_block=bubble.text_block,
            bubble_x=bubble.bubble_x,
            bubble_y=new_y,
            bubble_width=bubble.bubble_width,
            bubble_height=bubble.bubble_height,
            text_x=bubble.text_x,
            text_y=new_y + bubble.padding,
            padding=bubble.padding,
        )

        return new_bubble


if __name__ == "__main__":
    # テスト用コード
    print("=== core/layout.py テスト ===")

    # レイアウト計算機を作成
    calculator = TextLayoutCalculator()

    # セリフ吹き出しのテスト
    print("セリフ吹き出しレイアウトテスト:")
    serif_text = "ずっと待ってたんだから……"
    bubble_layout = calculator.calculate_serif_bubble_layout(
        serif_text, font_size=48, max_chars_per_line=10, position="top_right"
    )

    print(f"  テキスト: {serif_text}")
    print(f"  吹き出し位置: ({bubble_layout.bubble_x}, {bubble_layout.bubble_y})")
    print(
        f"  吹き出しサイズ: {bubble_layout.bubble_width} x {bubble_layout.bubble_height}"
    )
    print(f"  テキスト位置: ({bubble_layout.text_x}, {bubble_layout.text_y})")

    # ナレーションレイアウトのテスト
    print("\nナレーションレイアウトテスト:")
    narration_text = "そう言って、彼女は涙ぐんだ。長い間待っていた言葉だった。"
    narration_layout = calculator.calculate_narration_layout(
        narration_text, font_size=48, max_chars_per_line=20, alignment="center"
    )

    print(f"  テキスト: {narration_text}")
    print(f"  背景位置: ({narration_layout.bg_x}, {narration_layout.bg_y})")
    print(
        f"  背景サイズ: {narration_layout.bg_width} x {narration_layout.bg_height}"
    )
    print(f"  テキスト位置: ({narration_layout.text_x}, {narration_layout.text_y})")

    # 文字位置の計算テスト
    print("\n文字位置計算テスト:")
    positions = calculator.get_text_character_positions(bubble_layout)
    print(f"  文字数: {len(positions)}")
    if positions:
        print(
            f"  最初の文字: '{positions[0][2]}' at ({positions[0][0]}, {positions[0][1]})"
        )
        print(
            f"  最後の文字: '{positions[-1][2]}' at ({positions[-1][0]}, {positions[-1][1]})"
        )

    print("\nテスト完了")
