#!/usr/bin/env python3

import sys
import os
import subprocess
import unicodedata

def to_signed(b):
    """ 0〜255 の整数を符号付き8ビット整数に変換 """
    return b if b < 128 else b - 256

def detect_header(rom_data):
    """
    ROMファイルの先頭512バイトがヘッダーかどうかを推測する。
    PCE ROMの場合、最初の512バイトが0x00や0xFFで埋まっている場合はヘッダーと判断。
    """
    if len(rom_data) % 0x2000 == 512:
        if all(b in (0x00, 0xFF) for b in rom_data[:512]):
            print("512バイトのヘッダーを検出しました。スキップします。")
            return rom_data[512:]
    return rom_data

def search_candidates(rom_data):
    """
    バイト列中で、以下の差分パターンを持つ4バイトシーケンスを検索：
      +0x1C（28）, -7, +0x0C（12）
    """
    candidates = []
    for i in range(len(rom_data) - 3):
        seq = rom_data[i:i+4]
        a, b, c, d = seq[0], seq[1], seq[2], seq[3]
        diff0 = to_signed(a) - to_signed(b)
        diff1 = to_signed(b) - to_signed(c)
        diff2 = to_signed(c) - to_signed(d)
        if diff0 == 28 and diff1 == -7 and diff2 == 12:
            candidates.append((i, seq))
    return candidates

def convert_sequence(seq):
    """ 固定オフセット（0xA7）を加えてShift-JIS風に変換 """
    offset = 0xA7
    converted = bytes(((b + offset) & 0xFF) for b in seq)
    return converted

def decode_shift_jis(data):
    """ Shift-JISまたはCP932でデコード """
    try:
        return data.decode("cp932")
    except Exception:
        return "<デコード不可>"

def to_fullwidth(s):
    """ 半角→全角変換 """
    return unicodedata.normalize("NFKC", s)

def katakana_to_hiragana(s):
    """ カタカナ→ひらがな変換 """
    return "".join(chr(ord(ch) - 0x60) if 0x30A1 <= ord(ch) <= 0x30F6 else ch for ch in s)

def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py <rom_file.pce>")
        sys.exit(1)

    rom_path = sys.argv[1]
    if not os.path.exists(rom_path):
        print(f"ROMファイル '{rom_path}' が見つかりません。")
        sys.exit(1)

    with open(rom_path, "rb") as f:
        rom_data = f.read()

    rom_data = detect_header(rom_data)
    candidates = search_candidates(rom_data)

    output_lines = [f"検出された候補数: {len(candidates)}\n"]

    for offset, seq in candidates:
        conv = convert_sequence(seq)
        decoded = decode_shift_jis(conv)
        fullwidth = to_fullwidth(decoded)
        hiragana = katakana_to_hiragana(fullwidth)
        output_lines.append(
            f"オフセット 0x{offset:X}:\n"
            f"  元バイト列    : {' '.join(f'{b:02X}' for b in seq)}\n"
            f"  変換後バイト列: {' '.join(f'{b:02X}' for b in conv)}\n"
            f"  Shift-JIS文字 : {decoded}\n"
            f"  全角表示      : {fullwidth}\n"
            f"  ひらがな表示  : {hiragana}\n"
        )

    output_file = "hidden_passwords.txt"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(output_lines))
    print(f"結果を {output_file} に保存しました。")

    # GitHub Actionsで自動コミット＆プッシュ
    try:
        subprocess.run(["git", "config", "--global", "user.name", "github-actions"], check=True)
        subprocess.run(["git", "config", "--global", "user.email", "github-actions@github.com"], check=True)
        subprocess.run(["git", "add", output_file], check=True)
        subprocess.run(["git", "commit", "-m", "Extracted hidden passwords"], check=True)
        subprocess.run(["git", "push"], check=True)
        print("GitHubリポジトリにプッシュしました。")
    except subprocess.CalledProcessError as e:
        print("Git操作中にエラーが発生しました:", e)

if __name__ == "__main__":
    main()
