#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小説画像化ツール - GUIメインモジュール
TkinterベースのGUIインターフェース
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
import threading
from pathlib import Path
from typing import Dict, Callable, Optional, Any, Tuple, List
import sys
import os

# 相対インポート用のパス設定
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.parser import parse_novel_text
from core.renderer import render_novel_blocks
from core.utils import sanitize_filename, Constants


class NovelImageGeneratorGUI:
    """小説画像化ツールのGUIクラス"""

    def __init__(
        self,
        root: tk.Tk,
        initial_settings: Dict,
        save_callback: Callable,
        project_root: Path,
    ):
        self.root = root
        self.save_callback = save_callback
        self.project_root = project_root
        self.settings = initial_settings.copy()

        # GUI要素の辞書
        self.widgets = {}
        self.color_buttons = {}

        # 処理状態
        self.is_processing = False

        # GUIを構築
        self._setup_gui()
        self._load_initial_settings()

        # ウィンドウクローズ時の処理
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _setup_gui(self):
        """GUI要素を構築"""
        # スクロール可能なメインフレームを作成
        canvas = tk.Canvas(self.root)
        scrollbar = ttk.Scrollbar(
            self.root, orient="vertical", command=canvas.yview
        )
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # グリッド配置
        canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))

        # グリッドの重み設定
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        # メインフレーム（パディング付き）
        main_frame = ttk.Frame(scrollable_frame, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        main_frame.columnconfigure(1, weight=1)

        # マウスホイールでスクロール
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # タイトル
        title_label = ttk.Label(
            main_frame, text="📘 小説画像化ツール", font=("Arial", 16, "bold")
        )
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))

        current_row = 1

        # === 基本設定セクション ===
        current_row = self._create_basic_settings_section(
            main_frame, current_row
        )

        # === セリフ設定セクション ===
        current_row = self._create_serif_settings_section(
            main_frame, current_row
        )

        # === ナレーション設定セクション ===
        current_row = self._create_narration_settings_section(
            main_frame, current_row
        )

        # === ファイル設定セクション ===
        current_row = self._create_file_settings_section(
            main_frame, current_row
        )

        # === 実行ボタンセクション ===
        current_row = self._create_execution_section(main_frame, current_row)

        # === ログ表示セクション ===
        self._create_log_section(main_frame, current_row)

    def _create_basic_settings_section(
        self, parent: ttk.Frame, row: int
    ) -> int:
        """基本設定セクションを作成"""
        # セクションタイトル
        ttk.Label(parent, text="🎨 基本設定", font=("Arial", 12, "bold")).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=(10, 5)
        )
        row += 1

        # フォントファイル
        ttk.Label(parent, text="フォントファイル:").grid(
            row=row, column=0, sticky=tk.W, pady=2
        )
        font_frame = ttk.Frame(parent)
        font_frame.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=2)
        font_frame.columnconfigure(0, weight=1)

        self.widgets["font_path"] = ttk.Entry(font_frame, width=50)
        self.widgets["font_path"].grid(
            row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5)
        )
        ttk.Button(
            font_frame,
            text="参照",
            width=8,
            command=lambda: self._browse_file(
                "font_path",
                "フォントファイル",
                [("TrueTypeフォント", "*.ttf *.ttc"), ("すべて", "*.*")],
            ),
        ).grid(row=0, column=1)
        row += 1

        # フォントサイズ、カラー、最大文字数を1行にまとめる
        ttk.Label(parent, text="フォント設定:").grid(
            row=row, column=0, sticky=tk.W, pady=2
        )
        font_settings_frame = ttk.Frame(parent)
        font_settings_frame.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=2)

        # フォントサイズ
        ttk.Label(font_settings_frame, text="サイズ:").grid(
            row=0, column=0, padx=(0, 5)
        )
        self.widgets["font_size"] = ttk.Spinbox(
            font_settings_frame, from_=12, to=200, width=8
        )
        self.widgets["font_size"].grid(row=0, column=1, padx=(0, 10))

        # フォントカラー
        ttk.Label(font_settings_frame, text="色:").grid(
            row=0, column=2, padx=(0, 5)
        )
        self.widgets["font_color"] = ttk.Entry(font_settings_frame, width=10)
        self.widgets["font_color"].grid(row=0, column=3, padx=(0, 5))
        self.color_buttons["font_color"] = tk.Button(
            font_settings_frame,
            text="色選択",
            width=8,
            command=lambda: self._choose_color("font_color"),
        )
        self.color_buttons["font_color"].grid(row=0, column=4, padx=(0, 10))

        # 最大文字数
        ttk.Label(font_settings_frame, text="最大文字数:").grid(
            row=0, column=5, padx=(0, 5)
        )
        self.widgets["max_chars"] = ttk.Spinbox(
            font_settings_frame, from_=10, to=100, width=8
        )
        self.widgets["max_chars"].grid(row=0, column=6)
        row += 1

        return row

    def _create_serif_settings_section(
        self, parent: ttk.Frame, row: int
    ) -> int:
        """セリフ設定セクションを作成"""
        # セクションタイトル
        ttk.Label(
            parent, text="💬 セリフ設定（縦書き吹き出し）", font=("Arial", 12, "bold")
        ).grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=(15, 5))
        row += 1

        # セリフフォント
        ttk.Label(parent, text="セリフフォント:").grid(
            row=row, column=0, sticky=tk.W, pady=2
        )
        serif_font_frame = ttk.Frame(parent)
        serif_font_frame.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=2)
        serif_font_frame.columnconfigure(0, weight=1)

        self.widgets["serif_font_path"] = ttk.Entry(serif_font_frame, width=50)
        self.widgets["serif_font_path"].grid(
            row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5)
        )
        ttk.Button(
            serif_font_frame,
            text="参照",
            width=8,
            command=lambda: self._browse_file(
                "serif_font_path",
                "セリフフォント",
                [("TrueTypeフォント", "*.ttf"), ("すべて", "*.*")],
            ),
        ).grid(row=0, column=1)
        row += 1

        # セリフフォント色
        ttk.Label(parent, text="セリフフォント色:").grid(
            row=row, column=0, sticky=tk.W, pady=2
        )
        serif_color_frame = ttk.Frame(parent)
        serif_color_frame.grid(row=row, column=1, sticky=tk.W, pady=2)

        self.widgets["serif_font_color"] = ttk.Entry(
            serif_color_frame, width=10
        )
        self.widgets["serif_font_color"].grid(row=0, column=0, padx=(0, 5))
        self.color_buttons["serif_font_color"] = tk.Button(
            serif_color_frame,
            text="色選択",
            width=8,
            command=lambda: self._choose_color("serif_font_color"),
        )
        self.color_buttons["serif_font_color"].grid(row=0, column=1)
        row += 1

        # セリフ枠線色
        ttk.Label(parent, text="セリフ枠線色:").grid(
            row=row, column=0, sticky=tk.W, pady=2
        )
        border_color_frame = ttk.Frame(parent)
        border_color_frame.grid(row=row, column=1, sticky=tk.W, pady=2)

        self.widgets["serif_border_color"] = ttk.Entry(
            border_color_frame, width=10
        )
        self.widgets["serif_border_color"].grid(row=0, column=0, padx=(0, 5))
        self.color_buttons["serif_border_color"] = tk.Button(
            border_color_frame,
            text="色選択",
            width=8,
            command=lambda: self._choose_color("serif_border_color"),
        )
        self.color_buttons["serif_border_color"].grid(row=0, column=1)
        row += 1

        # セリフ背景色と透過度
        ttk.Label(parent, text="セリフ背景色:").grid(
            row=row, column=0, sticky=tk.W, pady=2
        )
        bg_color_frame = ttk.Frame(parent)
        bg_color_frame.grid(row=row, column=1, sticky=tk.W, pady=2)

        self.widgets["serif_bg_color"] = ttk.Entry(bg_color_frame, width=10)
        self.widgets["serif_bg_color"].grid(row=0, column=0, padx=(0, 5))
        self.color_buttons["serif_bg_color"] = tk.Button(
            bg_color_frame,
            text="色選択",
            width=8,
            command=lambda: self._choose_color("serif_bg_color"),
        )
        self.color_buttons["serif_bg_color"].grid(row=0, column=1)

        ttk.Label(bg_color_frame, text="透過度:").grid(
            row=0, column=2, padx=(10, 5)
        )
        self.widgets["serif_bg_alpha"] = ttk.Spinbox(
            bg_color_frame, from_=0, to=100, width=8
        )
        self.widgets["serif_bg_alpha"].grid(row=0, column=3)
        ttk.Label(bg_color_frame, text="%").grid(row=0, column=4, padx=(2, 0))
        row += 1

        return row

    def _create_narration_settings_section(
        self, parent: ttk.Frame, row: int
    ) -> int:
        """ナレーション設定セクションを作成"""
        # セクションタイトル
        ttk.Label(
            parent, text="📝 ナレーション設定（地の文）", font=("Arial", 12, "bold")
        ).grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=(15, 5))
        row += 1

        # ナレーション背景色と透過度
        ttk.Label(parent, text="ナレーション背景色:").grid(
            row=row, column=0, sticky=tk.W, pady=2
        )
        narr_bg_frame = ttk.Frame(parent)
        narr_bg_frame.grid(row=row, column=1, sticky=tk.W, pady=2)

        self.widgets["narration_bg_color"] = ttk.Entry(narr_bg_frame, width=10)
        self.widgets["narration_bg_color"].grid(row=0, column=0, padx=(0, 5))
        self.color_buttons["narration_bg_color"] = tk.Button(
            narr_bg_frame,
            text="色選択",
            width=8,
            command=lambda: self._choose_color("narration_bg_color"),
        )
        self.color_buttons["narration_bg_color"].grid(row=0, column=1)

        ttk.Label(narr_bg_frame, text="透過度:").grid(
            row=0, column=2, padx=(10, 5)
        )
        self.widgets["narration_bg_alpha"] = ttk.Spinbox(
            narr_bg_frame, from_=0, to=100, width=8
        )
        self.widgets["narration_bg_alpha"].grid(row=0, column=3)
        ttk.Label(narr_bg_frame, text="%").grid(row=0, column=4, padx=(2, 0))
        row += 1

        # ナレーション文字配置
        ttk.Label(parent, text="ナレーション文字配置:").grid(
            row=row, column=0, sticky=tk.W, pady=2
        )
        self.widgets["narration_text_align"] = ttk.Combobox(
            parent,
            values=["left", "center", "right"],
            state="readonly",
            width=15,
        )
        self.widgets["narration_text_align"].set("center")  # デフォルト値設定
        self.widgets["narration_text_align"].grid(
            row=row, column=1, sticky=tk.W, pady=2
        )
        row += 1

        # ナレーション向き
        ttk.Label(parent, text="ナレーション向き:").grid(
            row=row, column=0, sticky=tk.W, pady=2
        )
        self.widgets["narration_orientation"] = ttk.Combobox(
            parent,
            values=["horizontal", "vertical"],
            state="readonly",
            width=15,
        )
        self.widgets["narration_orientation"].set("horizontal")  # デフォルト値設定
        self.widgets["narration_orientation"].grid(
            row=row, column=1, sticky=tk.W, pady=2
        )
        row += 1

        return row

    def _create_file_settings_section(self, parent: ttk.Frame, row: int) -> int:
        """ファイル設定セクションを作成"""
        # セクションタイトル
        ttk.Label(parent, text="📁 ファイル設定", font=("Arial", 12, "bold")).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=(15, 5)
        )
        row += 1

        # 画像フォルダ
        ttk.Label(parent, text="画像フォルダ:").grid(
            row=row, column=0, sticky=tk.W, pady=2
        )
        img_folder_frame = ttk.Frame(parent)
        img_folder_frame.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=2)
        img_folder_frame.columnconfigure(0, weight=1)

        self.widgets["last_image_folder"] = ttk.Entry(
            img_folder_frame, width=50
        )
        self.widgets["last_image_folder"].grid(
            row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5)
        )
        ttk.Button(
            img_folder_frame,
            text="参照",
            width=8,
            command=lambda: self._browse_folder("last_image_folder", "画像フォルダ"),
        ).grid(row=0, column=1)
        row += 1

        # テキストファイル
        ttk.Label(parent, text="テキストファイル:").grid(
            row=row, column=0, sticky=tk.W, pady=2
        )
        text_file_frame = ttk.Frame(parent)
        text_file_frame.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=2)
        text_file_frame.columnconfigure(0, weight=1)

        self.widgets["last_text_file"] = ttk.Entry(text_file_frame, width=50)
        self.widgets["last_text_file"].grid(
            row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5)
        )
        ttk.Button(
            text_file_frame,
            text="参照",
            width=8,
            command=lambda: self._browse_file(
                "last_text_file",
                "テキストファイル",
                [("テキストファイル", "*.txt"), ("すべて", "*.*")],
            ),
        ).grid(row=0, column=1)
        row += 1

        # 出力フォルダ名
        ttk.Label(parent, text="出力フォルダ名:").grid(
            row=row, column=0, sticky=tk.W, pady=2
        )
        self.widgets["last_output_folder"] = ttk.Entry(parent, width=30)
        self.widgets["last_output_folder"].grid(
            row=row, column=1, sticky=tk.W, pady=2
        )
        row += 1

        return row

    def _create_execution_section(self, parent: ttk.Frame, row: int) -> int:
        """実行ボタンセクションを作成"""
        # セクションタイトル
        ttk.Label(parent, text="🚀 実行", font=("Arial", 12, "bold")).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=(15, 5)
        )
        row += 1

        # ボタンフレーム
        button_frame = ttk.Frame(parent)
        button_frame.grid(row=row, column=0, columnspan=2, pady=10)

        # 出力実行ボタン
        self.widgets["execute_button"] = ttk.Button(
            button_frame,
            text="🎨 画像生成開始",
            command=self._execute_generation,
            width=20,
        )
        self.widgets["execute_button"].grid(row=0, column=0, padx=5)

        # 設定保存ボタン
        ttk.Button(
            button_frame, text="💾 設定保存", command=self._save_settings, width=15
        ).grid(row=0, column=1, padx=5)

        # 設定読込ボタン
        ttk.Button(
            button_frame, text="📤 設定読込", command=self._load_settings, width=15
        ).grid(row=0, column=2, padx=5)

        # 出力フォルダを開くボタン
        ttk.Button(
            button_frame,
            text="📁 出力フォルダ",
            command=self._open_current_output_folder,
            width=15,
        ).grid(row=0, column=3, padx=5)

        # プログレスバー
        self.widgets["progress"] = ttk.Progressbar(parent, mode="indeterminate")
        self.widgets["progress"].grid(
            row=row + 1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5
        )

        return row + 2

    def _create_log_section(self, parent: ttk.Frame, row: int):
        """ログ表示セクションを作成"""
        # セクションタイトル
        ttk.Label(parent, text="📋 ログ", font=("Arial", 12, "bold")).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=(15, 5)
        )
        row += 1

        # ログテキストエリア
        log_frame = ttk.Frame(parent)
        log_frame.grid(
            row=row,
            column=0,
            columnspan=2,
            sticky=(tk.W, tk.E, tk.N, tk.S),
            pady=5,
        )
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        parent.rowconfigure(row, weight=1)

        self.widgets["log_text"] = tk.Text(log_frame, height=10, wrap=tk.WORD)
        log_scrollbar = ttk.Scrollbar(
            log_frame,
            orient=tk.VERTICAL,
            command=self.widgets["log_text"].yview,
        )
        self.widgets["log_text"].configure(yscrollcommand=log_scrollbar.set)

        self.widgets["log_text"].grid(
            row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S)
        )
        log_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))

    def _load_initial_settings(self):
        """初期設定をGUIに読み込み"""
        for key, widget in self.widgets.items():
            if key in self.settings and hasattr(widget, "delete"):
                if isinstance(widget, (ttk.Entry, ttk.Spinbox)):
                    widget.delete(0, tk.END)
                    widget.insert(0, str(self.settings[key]))
                elif isinstance(widget, ttk.Combobox):
                    widget.set(str(self.settings[key]))

        # 色ボタンの背景色を更新
        self._update_color_buttons()

    def _update_color_buttons(self):
        """色ボタンの背景色を更新"""
        color_keys = [
            "font_color",
            "serif_font_color",
            "serif_border_color",
            "serif_bg_color",
            "narration_bg_color",
        ]

        for key in color_keys:
            if key in self.widgets and key in self.color_buttons:
                try:
                    color_value = self.widgets[key].get()
                    if color_value.startswith("#") and len(color_value) == 7:
                        self.color_buttons[key].configure(bg=color_value)
                except:
                    pass

    def _browse_file(self, widget_key: str, title: str, filetypes: list):
        """ファイル選択ダイアログ"""
        filename = filedialog.askopenfilename(title=title, filetypes=filetypes)
        if filename:
            self.widgets[widget_key].delete(0, tk.END)
            self.widgets[widget_key].insert(0, filename)

    def _browse_folder(self, widget_key: str, title: str):
        """フォルダ選択ダイアログ"""
        folder = filedialog.askdirectory(title=title)
        if folder:
            self.widgets[widget_key].delete(0, tk.END)
            self.widgets[widget_key].insert(0, folder)

    def _choose_color(self, widget_key: str):
        """色選択ダイアログ"""
        current_color = self.widgets[widget_key].get()
        try:
            initial_color = (
                current_color if current_color.startswith("#") else "#000000"
            )
        except:
            initial_color = "#000000"

        color = colorchooser.askcolor(title="色を選択", initialcolor=initial_color)
        if color[1]:  # HEX値が返された場合
            self.widgets[widget_key].delete(0, tk.END)
            self.widgets[widget_key].insert(0, color[1])
            self.color_buttons[widget_key].configure(bg=color[1])

    def _get_current_settings(self) -> Dict:
        """現在のGUI設定を取得"""
        current_settings = {}

        for key, widget in self.widgets.items():
            if key in ["execute_button", "progress", "log_text"]:
                continue

            try:
                if isinstance(widget, (ttk.Entry, ttk.Spinbox)):
                    value = widget.get()
                elif isinstance(widget, ttk.Combobox):
                    value = widget.get()
                else:
                    continue

                # 数値フィールドの変換
                if key in [
                    "font_size",
                    "max_chars",
                    "serif_bg_alpha",
                    "narration_bg_alpha",
                ]:
                    try:
                        current_settings[key] = int(value) if value else 0
                    except ValueError:
                        current_settings[key] = 0
                else:
                    current_settings[key] = value

            except Exception as e:
                self._log(f"設定取得エラー ({key}): {e}")
                current_settings[key] = self.settings.get(key, "")

        return current_settings

    def _save_settings(self):
        """設定を保存"""
        try:
            current_settings = self._get_current_settings()
            if self.save_callback(current_settings):
                self.settings = current_settings
                self._log("設定を保存しました")
                messagebox.showinfo("保存完了", "設定が正常に保存されました")
            else:
                messagebox.showerror("保存エラー", "設定の保存に失敗しました")
        except Exception as e:
            self._log(f"設定保存エラー: {e}")
            messagebox.showerror("保存エラー", f"設定の保存中にエラーが発生しました:\n{e}")

    def _load_settings(self):
        """設定ファイルを読み込み"""
        config_file = filedialog.askopenfilename(
            title="設定ファイルを選択",
            filetypes=[("YAML設定ファイル", "*.yaml"), ("すべて", "*.*")],
        )

        if config_file:
            try:
                import yaml

                with open(config_file, "r", encoding="utf-8") as f:
                    loaded_settings = yaml.safe_load(f)

                if loaded_settings:
                    self.settings.update(loaded_settings)
                    self._load_initial_settings()
                    self._log(f"設定を読み込みました: {config_file}")
                    messagebox.showinfo("読み込み完了", "設定が正常に読み込まれました")
                else:
                    messagebox.showwarning("読み込み警告", "設定ファイルが空です")

            except Exception as e:
                self._log(f"設定読み込みエラー: {e}")
                messagebox.showerror("読み込みエラー", f"設定の読み込み中にエラーが発生しました:\n{e}")

    def _validate_settings(self) -> Tuple[bool, List[str]]:
        """設定の妥当性をチェック"""
        errors = []
        current_settings = self._get_current_settings()

        # 必須ファイルのチェック
        image_folder = current_settings.get("last_image_folder", "").strip()
        text_file = current_settings.get("last_text_file", "").strip()
        output_folder = current_settings.get("last_output_folder", "").strip()

        if not image_folder or not Path(image_folder).exists():
            errors.append("画像フォルダが指定されていないか、存在しません")

        if not text_file or not Path(text_file).exists():
            errors.append("テキストファイルが指定されていないか、存在しません")

        if not output_folder:
            errors.append("出力フォルダ名が指定されていません")

        # 数値設定のチェック
        if current_settings.get("font_size", 0) < 12:
            errors.append("フォントサイズは12以上で指定してください")

        if current_settings.get("max_chars", 0) < 1:
            errors.append("最大文字数は1以上で指定してください")

        return len(errors) == 0, errors

    def _execute_generation(self):
        """画像生成を実行"""
        if self.is_processing:
            messagebox.showwarning("処理中", "既に画像生成処理が実行中です")
            return

        # 設定の妥当性チェック
        is_valid, errors = self._validate_settings()
        if not is_valid:
            error_message = "以下のエラーを修正してください:\n\n" + "\n".join(
                f"• {error}" for error in errors
            )
            messagebox.showerror("設定エラー", error_message)
            return

        # 確認ダイアログ
        if not messagebox.askyesno("実行確認", "画像生成を開始しますか？"):
            return

        # 設定を自動保存
        self._save_settings()

        # 別スレッドで処理を実行
        self.is_processing = True
        self._update_ui_state(False)

        thread = threading.Thread(target=self._generation_worker, daemon=True)
        thread.start()

    def _generation_worker(self):
        """画像生成のワーカーメソッド（別スレッド）"""
        try:
            self._log("=" * 50)
            self._log("画像生成を開始します...")

            current_settings = self._get_current_settings()

            # テキスト解析
            self._log("1. テキストファイルを解析中...")
            text_file = current_settings["last_text_file"]
            blocks, warnings = parse_novel_text(text_file)

            self._log(f"   解析完了: {len(blocks)}個のブロックを検出")

            # 警告があれば表示
            if warnings:
                self._log("⚠️ 警告:")
                for warning in warnings:
                    self._log(f"   {warning}")

            # 画像生成
            self._log("2. 画像生成中...")
            image_folder = current_settings["last_image_folder"]
            output_folder = (
                self.project_root
                / "output"
                / sanitize_filename(current_settings["last_output_folder"])
            )
            base_name = sanitize_filename(
                current_settings["last_output_folder"]
            )

            # 出力設定を追加
            render_settings = current_settings.copy()
            render_settings.update(
                {
                    "output_width": Constants.DEFAULT_WIDTH,
                    "output_height": Constants.DEFAULT_HEIGHT,
                }
            )

            success, render_errors = render_novel_blocks(
                blocks,
                image_folder,
                str(output_folder),
                base_name,
                render_settings,
            )

            # 結果表示
            if success:
                self._log("✅ 画像生成が正常に完了しました")
                self._log(f"   出力先: {output_folder}")
                self._log(f"   生成枚数: {len(blocks)}枚")

                # エクスプローラーで出力フォルダを開く
                self._open_output_folder(str(output_folder))

                # 完了ダイアログ（メインスレッドで実行）
                self.root.after(
                    0,
                    lambda: messagebox.showinfo(
                        "生成完了",
                        f"画像生成が正常に完了しました。\n\n"
                        f"出力先: {output_folder}\n"
                        f"生成枚数: {len(blocks)}枚\n\n"
                        f"出力フォルダをエクスプローラーで開きました。",
                    ),
                )
            else:
                self._log("❌ 画像生成中にエラーが発生しました")
                for error in render_errors:
                    self._log(f"   エラー: {error}")

                # エラーダイアログ（メインスレッドで実行）
                error_message = "画像生成中にエラーが発生しました:\n\n" + "\n".join(
                    render_errors[:5]
                )
                if len(render_errors) > 5:
                    error_message += f"\n\n... 他 {len(render_errors) - 5} 件のエラー"

                self.root.after(
                    0, lambda: messagebox.showerror("生成エラー", error_message)
                )

        except Exception as e:
            self._log(f"❌ 予期しないエラー: {e}")
            import traceback

            self._log("スタックトレース:")
            self._log(traceback.format_exc())

            # エラーダイアログ（メインスレッドで実行）
            self.root.after(
                0,
                lambda: messagebox.showerror(
                    "予期しないエラー", f"画像生成中に予期しないエラーが発生しました:\n\n{e}"
                ),
            )

        finally:
            # UI状態を復元（メインスレッドで実行）
            self.root.after(0, lambda: self._update_ui_state(True))
            self.root.after(0, lambda: setattr(self, "is_processing", False))
            self._log("=" * 50)

    def _update_ui_state(self, enabled: bool):
        """UI要素の有効/無効を切り替え"""
        state = tk.NORMAL if enabled else tk.DISABLED

        # ボタンとエントリーの状態を更新
        for key, widget in self.widgets.items():
            if key == "log_text":
                continue

            try:
                if hasattr(widget, "configure"):
                    if key == "execute_button":
                        widget.configure(state=state)
                        if enabled:
                            widget.configure(text="🎨 画像生成開始")
                        else:
                            widget.configure(text="⏳ 処理中...")
                    else:
                        widget.configure(state=state)
            except:
                pass

        # プログレスバーの制御
        if enabled:
            self.widgets["progress"].stop()
        else:
            self.widgets["progress"].start()

        # 色ボタンの状態更新
        for button in self.color_buttons.values():
            try:
                button.configure(state=state)
            except:
                pass

    def _log(self, message: str):
        """ログにメッセージを追加"""
        import datetime

        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"

        # メインスレッドで実行されているかチェック
        try:
            if threading.current_thread() == threading.main_thread():
                self._append_log_direct(log_message)
            else:
                # 別スレッドからの場合はメインスレッドにスケジュール
                self.root.after(0, lambda: self._append_log_direct(log_message))
        except:
            # フォールバック: コンソールに出力
            print(f"LOG: {message}")

    def _open_current_output_folder(self):
        """現在設定されている出力フォルダを開く"""
        try:
            current_settings = self._get_current_settings()
            output_folder_name = current_settings.get(
                "last_output_folder", ""
            ).strip()

            if not output_folder_name:
                messagebox.showwarning("警告", "出力フォルダ名が設定されていません")
                return

            # プロジェクトルートのoutputフォルダを基準にする
            output_folder = (
                self.project_root
                / "output"
                / sanitize_filename(output_folder_name)
            )

            if not output_folder.exists():
                # フォルダが存在しない場合は作成
                output_folder.mkdir(parents=True, exist_ok=True)
                self._log(f"出力フォルダを作成しました: {output_folder}")

            self._open_output_folder(str(output_folder))
            self._log(f"出力フォルダを開きました: {output_folder}")

        except Exception as e:
            self._log(f"出力フォルダを開けませんでした: {e}")
            messagebox.showerror("エラー", f"出力フォルダを開けませんでした:\n{e}")

    def _open_output_folder(self, folder_path: str):
        """
        出力フォルダをエクスプローラーで開く

        Args:
            folder_path: 開くフォルダのパス
        """
        try:
            import subprocess
            import platform

            folder_path = str(Path(folder_path).resolve())

            system = platform.system()
            if system == "Windows":
                # Windows: エクスプローラーで開く
                subprocess.run(["explorer", folder_path], check=False)
            elif system == "Darwin":  # macOS
                # macOS: Finderで開く
                subprocess.run(["open", folder_path], check=False)
            elif system == "Linux":
                # Linux: ファイルマネージャーで開く
                subprocess.run(["xdg-open", folder_path], check=False)
            else:
                self._log(f"   エクスプローラーの自動起動は対応していません: {system}")

        except Exception as e:
            self._log(f"   エクスプローラー起動エラー: {e}")
            # エラーが発生してもプログラムは継続

    def _append_log_direct(self, log_message: str):
        """ログテキストに直接追加（メインスレッド用）"""
        try:
            self.widgets["log_text"].insert(tk.END, log_message)
            self.widgets["log_text"].see(tk.END)
            self.root.update_idletasks()
        except:
            pass

    def _on_closing(self):
        """ウィンドウクローズ時の処理"""
        if self.is_processing:
            if messagebox.askokcancel("終了確認", "画像生成処理が実行中です。終了しますか？"):
                self.root.destroy()
        else:
            # 設定を自動保存
            try:
                current_settings = self._get_current_settings()
                self.save_callback(current_settings)
            except:
                pass
            self.root.destroy()


class SettingsValidator:
    """設定の妥当性を検証するクラス"""

    @staticmethod
    def validate_color(color_str: str) -> bool:
        """HEX色コードの妥当性をチェック"""
        if not color_str.startswith("#"):
            return False

        if len(color_str) != 7:
            return False

        try:
            int(color_str[1:], 16)
            return True
        except ValueError:
            return False

    @staticmethod
    def validate_file_path(file_path: str) -> bool:
        """ファイルパスの存在をチェック"""
        return file_path and Path(file_path).exists()

    @staticmethod
    def validate_folder_path(folder_path: str) -> bool:
        """フォルダパスの存在をチェック"""
        return (
            folder_path
            and Path(folder_path).exists()
            and Path(folder_path).is_dir()
        )

    @staticmethod
    def validate_positive_int(value: str, min_value: int = 1) -> bool:
        """正の整数かをチェック"""
        try:
            int_value = int(value)
            return int_value >= min_value
        except ValueError:
            return False


def create_gui_application(
    initial_settings: Dict, save_callback: Callable, project_root: Path
) -> NovelImageGeneratorGUI:
    """
    GUIアプリケーションを作成する便利関数

    Args:
        initial_settings: 初期設定辞書
        save_callback: 設定保存コールバック関数
        project_root: プロジェクトルートパス

    Returns:
        NovelImageGeneratorGUI: 作成されたGUIアプリケーション
    """
    root = tk.Tk()
    root.title("小説画像化ツール")
    root.geometry("900x920")  # 縦を920pxに拡大
    root.minsize(800, 700)  # 最小サイズも調整

    # アイコン設定（オプション）
    try:
        # ICOファイルがある場合
        icon_path = project_root / "assets" / "icon.ico"
        if icon_path.exists():
            root.iconbitmap(str(icon_path))
    except:
        pass

    app = NovelImageGeneratorGUI(
        root, initial_settings, save_callback, project_root
    )
    return app


if __name__ == "__main__":
    # テスト用のGUI起動
    print("=== GUI テストモード ===")

    # テスト用設定
    test_settings = {
        "font_path": "",
        "font_size": 48,
        "font_color": "#000000",
        "serif_font_path": "",
        "serif_font_color": "#2A2A2A",
        "serif_bg_color": "#FFFFFF",
        "serif_bg_alpha": 30,
        "serif_border_color": "#3C4C6A",
        "narration_bg_color": "#003232",
        "narration_bg_alpha": 30,
        "narration_text_align": "center",
        "narration_orientation": "horizontal",
        "max_chars": 35,
        "last_image_folder": "",
        "last_text_file": "",
        "last_output_folder": "test_output",
    }

    # テスト用保存コールバック
    def test_save_callback(settings):
        print("設定保存テスト:", settings)
        return True

    # プロジェクトルート
    project_root = Path(__file__).parent.parent

    # GUI作成・起動
    try:
        app = create_gui_application(
            test_settings, test_save_callback, project_root
        )
        app.root.mainloop()
    except Exception as e:
        print(f"GUIテストエラー: {e}")
        import traceback

        traceback.print_exc()
