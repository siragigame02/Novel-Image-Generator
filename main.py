#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小説画像化ツール - メインエントリーポイント
CG集形式の画像を自動生成するGUIツール
"""

import os
import sys
import yaml
from pathlib import Path
import tkinter as tk
from tkinter import messagebox


# プロジェクトルートディレクトリを設定
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# 各モジュールのインポート
try:
    from gui.gui_main import NovelImageGeneratorGUI
    from core.utils import ensure_directory_exists
except ImportError as e:
    print(f"モジュールのインポートに失敗しました: {e}")
    print("必要なモジュールが見つかりません。ディレクトリ構成を確認してください。")
    sys.exit(1)


class NovelImageGeneratorApp:
    """小説画像化ツールのメインアプリケーションクラス"""

    def __init__(self):
        self.project_root = PROJECT_ROOT
        self.config_dir = self.project_root / "config"
        self.config_file = self.config_dir / "settings.yaml"
        self.output_dir = self.project_root / "output"

        # 必要なディレクトリを作成
        self._initialize_directories()

        # 設定の初期化
        self.settings = self._load_settings()

    def _initialize_directories(self):
        """必要なディレクトリを初期化"""
        directories = [
            self.config_dir,
            self.output_dir,
            self.project_root / "assets" / "default_fonts",
        ]

        for directory in directories:
            ensure_directory_exists(directory)
            print(f"ディレクトリを確認/作成: {directory}")

    def _load_settings(self):
        """設定ファイルを読み込み"""
        default_settings = {
            # フォント設定
            "font_path": "",
            "font_size": 48,
            "font_color": "#000000",
            # セリフ設定
            "serif_font_path": "",
            "serif_font_color": "#2A2A2A",
            "serif_bg_color": "#FFFFFF",
            "serif_bg_alpha": 30,
            "serif_border_color": "#3C4C6A",
            # ナレーション設定
            "narration_bg_color": "#003232",
            "narration_bg_alpha": 30,
            "narration_text_align": "center",
            "narration_orientation": "horizontal",
            # その他の設定
            "max_chars": 35,
            "last_image_folder": "",
            "last_text_file": "",
            "last_output_folder": "",
            # 出力設定
            "output_width": 960,
            "output_height": 1280,
            "output_format": "jpg",
        }

        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    loaded_settings = yaml.safe_load(f) or {}

                # デフォルト設定を読み込んだ設定で更新
                default_settings.update(loaded_settings)
                print(f"設定ファイルを読み込みました: {self.config_file}")

            except Exception as e:
                print(f"設定ファイル読み込みエラー: {e}")
                messagebox.showwarning(
                    "設定読み込みエラー",
                    f"設定ファイルの読み込みに失敗しました。\nデフォルト設定を使用します。\n\nエラー: {e}",
                )
        else:
            print("設定ファイルが見つかりません。デフォルト設定を使用します。")

        return default_settings

    def save_settings(self, settings):
        """設定をファイルに保存"""
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                yaml.dump(
                    settings,
                    f,
                    default_flow_style=False,
                    allow_unicode=True,
                    indent=2,
                )
            print(f"設定を保存しました: {self.config_file}")
            return True

        except Exception as e:
            print(f"設定保存エラー: {e}")
            messagebox.showerror("設定保存エラー", f"設定の保存に失敗しました。\n\nエラー: {e}")
            return False

    def run(self):
        """アプリケーションを起動"""
        try:
            # Tkinterのルートウィンドウを作成
            root = tk.Tk()
            root.title("小説画像化ツール")

            # ウィンドウサイズとアイコンの設定
            root.geometry("900x600")
            root.minsize(600, 860)

            # GUIアプリケーションを作成
            app = NovelImageGeneratorGUI(
                root,
                initial_settings=self.settings,
                save_callback=self.save_settings,
                project_root=self.project_root,
            )

            print("小説画像化ツールを起動しました。")
            print(f"プロジェクトルート: {self.project_root}")
            print(f"設定ファイル: {self.config_file}")
            print(f"出力ディレクトリ: {self.output_dir}")

            # メインループ開始
            root.mainloop()

        except Exception as e:
            print(f"アプリケーション起動エラー: {e}")
            messagebox.showerror("起動エラー", f"アプリケーションの起動に失敗しました。\n\nエラー: {e}")
            sys.exit(1)


def check_dependencies():
    """必要な依存関係をチェック"""
    required_modules = [
        ("yaml", "PyYAML"),
        ("PIL", "Pillow"),
        ("tkinter", "tkinter (標準ライブラリ)"),
    ]

    missing_modules = []

    for module_name, package_name in required_modules:
        try:
            __import__(module_name)
        except ImportError:
            missing_modules.append(package_name)

    if missing_modules:
        print("以下のパッケージが不足しています:")
        for package in missing_modules:
            print(f"  - {package}")
        print("\n以下のコマンドでインストールしてください:")
        for package in missing_modules:
            if package != "tkinter (標準ライブラリ)":
                print(f"  pip install {package.split()[0].lower()}")
        return False

    return True


def main():
    """メイン関数"""
    print("=" * 50)
    print("小説画像化ツール starting...")
    print("=" * 50)

    # 依存関係チェック
    if not check_dependencies():
        print("依存関係の問題により起動を中止します。")
        input("Enterキーを押して終了...")
        sys.exit(1)

    try:
        # アプリケーションインスタンスを作成・実行
        app = NovelImageGeneratorApp()
        app.run()

    except KeyboardInterrupt:
        print("\nユーザーによる中断")
        sys.exit(0)

    except Exception as e:
        print(f"予期しないエラーが発生しました: {e}")
        import traceback

        traceback.print_exc()
        input("Enterキーを押して終了...")
        sys.exit(1)


if __name__ == "__main__":
    main()
