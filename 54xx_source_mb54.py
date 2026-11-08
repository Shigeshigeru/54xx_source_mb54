#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ボスコニアン用 代替 54xx.bin 作成ツール (FBNeo 用)
=====================================================

■ これは何か
  Namco 54xx(爆発音ノイズ発生チップ, 富士通 MB8844)の内蔵プログラム `54xx.bin`(1024バイト)の
  代わりになる、爆発ノイズ発生プログラムを、一から書いて生成するツールです。
  本物と同じ中身ではありません。FBNeo の mb88xx.cpp(MB88xx コア)の動作に合わせて
  作ってあり、ノイズのバースト(急に大きく → 徐々に小さく)を鳴らします。

■ 必要なもの
  Python 3.8 以上(標準ライブラリのみ。追加インストール不要)

■ 基本の使い方
  python 54xx_source_mb54.py                      → 初期設定で 54xx.bin を作る
  python 54xx_source_mb54.py --info               → 作成後に、速度・減衰時間などを表示する
  python 54xx_source_mb54.py --test               → 自己テスト(エミュレータで動作確認)
  python 54xx_source_mb54.py --preview prev       → prev フォルダに確認用 WAV を書き出す
  python 54xx_source_mb54.py --into-zip bosco1.zip → zip の中の 54xx.bin を差し替える

  オプションは組み合わせられます。例:
  python 54xx_source_mb54.py --level0 12 --level1 10 --level2 6 --decay-div 3 --test --info

■ パラメーター(コマンドラインオプション)の説明
  --level0 / --level1 / --level2   (0〜15, 初期値 15)
        各出力の「鳴り始めの音量」です。数字が大きいほど大きく、長く鳴ります。
        出力0=低い「ゴォー」(約170Hz帯), 出力1=中音(約450Hz帯), 出力2=「ザー」(約2.5kHz帯)
        例: 低音を強く、ザーを弱くしたい → --level0 15 --level2 6

  --decay-div0 / --decay-div1 / --decay-div2   (1〜16, 初期値 8)
        各出力ごとの「減衰の遅さ」です。音量が1段階下がるまでの時間(64回ループ ≒ 13.6ミリ秒 × この値)で、
        大きいほどゆっくり消えます。出力ごとに独立して設定できます。
        音量15→0 までの目安: 4 → 約0.8秒 / 8 → 約1.6秒 / 12 → 約2.4秒 / 16 → 約3.3秒
        例: 低音は長く、ザーは短く → --decay-div0 12 --decay-div1 9 --decay-div2 4

  --decay-mode                     (初期値 すべて lin。例 "lin,lin,exp")
        出力ごとの「減衰の形」です。lin=音量が一定の間隔で1ずつ下がる(爆発音向き)、
        exp=音量が「現在の音量の約1/4ずつ」下がる指数的な減衰で、最初は急に、最後はゆっくり消える
        (15→11→8→6→4→3→2→1→0)。アタック感があり、キレのある音になります(ショット音向き)。
        元のショット音は、約0.12秒ごとに音量が約7割になる指数的な減衰でした
        (--decay-div 9 の exp で、約1秒の長さと、音量の比率がほぼ一致します)。

  --decay-div                      (1〜16)
        上の3つをまとめて同じ値にする近道です。個別指定(--decay-div0〜2)があれば、そちらが優先。

  --seed                           (16bit の16進数, 初期値 0xC3A5, 0 は不可)
        ノイズ(乱数)の初期値です。音の「ザラつき方」が少し変わるだけで、通常は変更不要です。

  --pad-nops                       (0〜60, 初期値 0)
        メインループに何もしない命令を足して、ノイズの更新を遅くします。
        増やすと、ノイズが低域寄り(こもった音)になり、減衰も比例して長くなります。

  --trigger                        (初期値 "1:0,2:1,5:2")
        「命令の上位4ビット : 鳴らす出力」の対応表です。1:0 は、命令 0x1n で出力0を鳴らす意味。
        例: 0x1n で出力1を鳴らしたい → --trigger "1:1,2:1,5:2"

  --mix                            (初期値 なし)
        1つの命令で、複数の出力を、出力ごとの音量で同時に鳴らします(--trigger/--level より優先)。
        書式: "命令の上位4bit:出力=音量,出力=音量;次の命令の上位4bit:…"
        例: --mix "1:0=15,1=7,2=7;2:0=11,1=15"
            → 命令 0x1n で 出力0=15, 出力1=7, 出力2=7 / 命令 0x2n で 出力0=11, 出力1=15
        ※ 元の爆発音は、低音・中音・高音が混ざった音なので、単独の出力より、混ぜたほうが近づきます。

  --skip                           (初期値 "3:4,4:4,6:5")
        「命令の上位4ビット : 続く設定バイトの数」です。3:4 は、命令 0x3n のあとの4バイトを
        設定データとして読み飛ばす意味(54xx の本来の通信形式。変更不要)。

  --out FILE                       出力ファイル名(初期値 54xx.bin)
  --into-zip ZIP                   既存の zip(例 bosco1.zip)内の 54xx.bin を、作成したもので
                                   差し替える(元の zip は ZIP名.bak にコピーして残します)
  --test                           自己テストを実行
  --info                           作成後の特性(ループ速度、減衰時間)を表示
  --preview DIR                    FBNeo と同じフィルタを通した確認用 WAV を DIR に書き出す

■ 何が独立で、何が共通か
  [出力ごとに独立]  鳴り始めの音量(--level)・減衰の遅さ(--decay-div0/1/2)・発音の命令との対応(--trigger)
                    → 3つの出力は、それぞれ別の音量カウンタと、別の減衰カウンタを持ちます。
                      ある出力が鳴っている最中に別の出力を鳴らしても、互いに影響しません。
  [3つで共通]       ノイズの元(16bit 乱数 1個。出力ごとに別のビット位置を使用)
                    ノイズの更新速度(約4.7kHz。--pad-nops で全体が変わる)
                    減衰の基準タイマー(256ループごと)
  ※ MB8844 は CPU が1つなので、3つの出力は、1つのループの中で順番に更新しています(同時処理)。

■ MB8844 の RAM の使い方(上級者向け)
   0: A の退避   4: Y の退避   5: 命令の上位4bit   2,3: 減衰の基準タイマー(下位/上位)
   6,7,1: 出力0,1,2 の減衰カウンタ
   (減衰の基準タイマー: 2 が16ループ、3 が4周で、64ループごと)
   8〜11: 16bit 乱数 N0〜N3(N3 が最上位)   12,13,14: 出力0,1,2 の音量   15: 読み飛ばす残りバイト数
"""
import argparse, math, os, shutil, struct, sys, wave, zipfile, random

# ======================================================================== 初期設定
DEFAULTS = dict(
    level=[15, 15, 15],            # 各出力の鳴り始めの音量 (0-15)
    decay_div=[8, 8, 8],           # 出力ごとの減衰の間隔 (64ループ × この値)
    mix={},                        # 命令 -> [(出力, 音量), ...] 複数出力の同時発音
    decay_mode=['lin', 'lin', 'lin'],  # 出力ごとの減衰の形: 'lin'=直線, 'exp'=指数(アタックが強く、キレのある音)
    seed=0xC3A5,                   # 乱数の初期値
    pad_nops=0,                    # ループに足す nop の数
    trigger={1: 0, 2: 1, 5: 2},    # 命令の上位4bit -> 鳴らす出力
    skip={3: 4, 4: 4, 6: 5},       # 命令の上位4bit -> 続く設定バイト数
)
CYC_PER_SEC = 4266 * 60            # FBNeo: 54xx は 1フレーム 4266 サイクル × 60fps


# ======================================================================== MB8844 エミュレータ
class MB88:
    """FBNeo の burn/devices/mb88xx.cpp と同じ動作をする MB8844 エミュレータ(テスト用)。"""

    def __init__(s, rom):
        s.rom = bytearray(rom) + bytearray(0x400 - len(rom))
        s.ram = [0] * 64
        s.read_k = lambda: 0
        s.read_r = [lambda: 0] * 4
        s.write_o = lambda v: None
        s.write_r = [lambda v: None] * 4
        s.cycles = 0
        s.reset()

    def reset(s):
        s.PC = s.PA = 0
        s.SP = [0] * 4; s.SI = 0
        s.A = s.X = s.Y = 0
        s.st = 1; s.zf = s.cf = s.vf = s.sf = s.nf = 0
        s.pio = 0; s.pending = 0; s.in_irq = 0
        s.TH = s.TL = s.SB = 0

    def ST_C(s, v): s.st = 0 if (v & 0x10) else 1
    def ST_Z(s, v): s.st = 0 if v == 0 else 1
    def CF_(s, v): s.cf = 1 if (v & 0x10) else 0
    def ZF_(s, v): s.zf = 1 if v == 0 else 0
    def pc(s): return (s.PA << 6) + s.PC

    def incpc(s):
        s.PC += 1
        if s.PC >= 0x40:
            s.PC = 0; s.PA += 1

    def ea(s): return (s.X << 4) + s.Y
    def rd(s, a): return s.ram[a & 0x3f] & 0x0f
    def wr(s, a, v): s.ram[a & 0x3f] = v & 0x0f
    def readop(s, a): return s.rom[a & 0x3ff]

    def set_irq(s, state):
        if (s.pio & 4) and not s.nf and state:
            s.pending |= 4
        s.nf = 1 if state else 0

    def update_pio(s):
        if (not s.in_irq) and (s.pending & s.pio):
            s.in_irq = 1
            s.SP[s.SI] = s.pc() | (s.cf << 15) | (s.zf << 14) | (s.st << 13)
            s.SI = (s.SI + 1) & 3
            if s.pending & s.pio & 4: s.PC = 2
            elif s.pending & s.pio & 2: s.PC = 4
            elif s.pending & s.pio & 1: s.PC = 6
            s.PA = 0; s.st = 1; s.pending = 0
            s.cycles += 3

    def step(s):
        op = s.readop(s.pc()); s.incpc(); oc = 1
        if op == 0x00: s.st = 1
        elif op == 0x01: s.write_o(((s.cf & 1) << 4) | (s.A & 15)); s.st = 1
        elif op == 0x02: s.st = 1
        elif op == 0x03: s.write_r[s.Y & 3](s.A); s.st = 1
        elif op == 0x04: s.Y = s.A; s.st = 1
        elif op == 0x05: s.TH = s.A; s.st = 1
        elif op == 0x06: s.TL = s.A; s.st = 1
        elif op == 0x07: s.SB = s.A; s.st = 1
        elif op == 0x08: s.Y += 1; s.ST_C(s.Y); s.Y &= 15; s.ZF_(s.Y)
        elif op == 0x09:
            a = s.rd(s.ea()) + 1; s.ST_C(a); a &= 15; s.ZF_(a); s.wr(s.ea(), a)
        elif op == 0x0a:
            s.wr(s.ea(), s.A); s.Y += 1; s.ST_C(s.Y); s.Y &= 15; s.ZF_(s.Y)
        elif op == 0x0b:
            a = s.rd(s.ea()); s.wr(s.ea(), s.A); s.A = a; s.ZF_(s.A); s.st = 1
        elif op == 0x0c:
            s.A = (s.A << 1) | s.cf; s.ST_C(s.A); s.cf = s.st ^ 1; s.A &= 15; s.ZF_(s.A)
        elif op == 0x0d: s.A = s.rd(s.ea()); s.ZF_(s.A); s.st = 1
        elif op == 0x0e:
            a = s.rd(s.ea()) + s.A + s.cf; s.ST_C(a); s.cf = s.st ^ 1; s.A = a & 15; s.ZF_(s.A)
        elif op == 0x0f:
            s.A &= s.rd(s.ea()); s.ZF_(s.A); s.st = s.zf ^ 1
        elif op == 0x10:
            if s.cf or s.A > 9: s.A += 6
            s.ST_C(s.A); s.cf = s.st ^ 1; s.A &= 15
        elif op == 0x11:
            if s.cf or s.A > 9: s.A += 10
            s.ST_C(s.A); s.cf = s.st ^ 1; s.A &= 15
        elif op == 0x12: s.A = s.read_k() & 15; s.ZF_(s.A); s.st = 1
        elif op == 0x13: s.A = s.read_r[s.Y & 3]() & 15; s.ZF_(s.A); s.st = 1
        elif op == 0x14: s.A = s.Y; s.ZF_(s.A); s.st = 1
        elif op == 0x15: s.A = s.TH; s.ZF_(s.A); s.st = 1
        elif op == 0x16: s.A = s.TL; s.ZF_(s.A); s.st = 1
        elif op == 0x17: s.A = s.SB; s.ZF_(s.A); s.st = 1
        elif op == 0x18: s.Y = (s.Y - 1) & 0xff; s.ST_C(s.Y); s.Y &= 15
        elif op == 0x19:
            a = (s.rd(s.ea()) - 1) & 0xff; s.ST_C(a); a &= 15; s.ZF_(a); s.wr(s.ea(), a)
        elif op == 0x1a:
            s.wr(s.ea(), s.A); s.Y = (s.Y - 1) & 0xff; s.ST_C(s.Y); s.Y &= 15; s.ZF_(s.Y)
        elif op == 0x1b: a = s.X; s.X = s.A; s.A = a; s.ZF_(s.A); s.st = 1
        elif op == 0x1c:
            s.A |= s.cf << 4; s.ST_C(s.A << 4); s.cf = s.st ^ 1; s.A >>= 1; s.A &= 15; s.ZF_(s.A)
        elif op == 0x1d: s.wr(s.ea(), s.A); s.st = 1
        elif op == 0x1e:
            a = (s.rd(s.ea()) - s.A - s.cf) & 0xff; s.ST_C(a); s.cf = s.st ^ 1; s.A = a & 15; s.ZF_(s.A)
        elif op == 0x1f:
            s.A |= s.rd(s.ea()); s.ZF_(s.A); s.st = s.zf ^ 1
        elif op == 0x20:
            a = s.read_r[s.Y // 4]() & 15; s.write_r[s.Y // 4](a | (1 << (s.Y % 4))); s.st = 1
        elif op == 0x21: s.cf = 1; s.st = 1
        elif op == 0x22:
            a = s.read_r[s.Y // 4]() & 15; s.write_r[s.Y // 4](a & ~(1 << (s.Y % 4))); s.st = 1
        elif op == 0x23: s.cf = 0; s.st = 1
        elif op == 0x24:
            a = s.read_r[s.Y // 4]() & 15; s.st = 0 if (a & (1 << (s.Y % 4))) else 1
        elif op == 0x25: s.st = s.nf ^ 1
        elif op == 0x26: s.st = s.vf ^ 1; s.vf = 0
        elif op == 0x27: s.st = s.sf ^ 1; s.sf = 0
        elif op == 0x28: s.st = s.cf ^ 1
        elif op == 0x29: s.st = s.zf ^ 1
        elif op == 0x2a: s.wr(s.ea(), s.SB); s.ZF_(s.SB); s.st = 1
        elif op == 0x2b: s.SB = s.rd(s.ea()); s.ZF_(s.SB); s.st = 1
        elif op == 0x2c:
            s.SI = (s.SI - 1) & 3; s.PC = s.SP[s.SI] & 0x3f; s.PA = (s.SP[s.SI] >> 6) & 0x1f; s.st = 1
        elif op == 0x2d: s.A = ((~s.A) + 1) & 15; s.ST_Z(s.A)
        elif op == 0x2e:
            a = (s.rd(s.ea()) - s.A) & 0xff; s.CF_(a); a &= 15; s.ST_Z(a); s.zf = s.st ^ 1
        elif op == 0x2f:
            s.A ^= s.rd(s.ea()); s.ST_Z(s.A); s.zf = s.st ^ 1
        elif 0x30 <= op <= 0x33: s.wr(s.ea(), s.rd(s.ea()) | (1 << (op & 3))); s.st = 1
        elif 0x34 <= op <= 0x37: s.wr(s.ea(), s.rd(s.ea()) & ~(1 << (op & 3))); s.st = 1
        elif 0x38 <= op <= 0x3b: s.st = 0 if (s.rd(s.ea()) & (1 << (op & 3))) else 1
        elif op == 0x3c:
            s.in_irq = 0; s.SI = (s.SI - 1) & 3
            v = s.SP[s.SI]; s.PC = v & 0x3f; s.PA = (v >> 6) & 0x1f
            s.st = (v >> 13) & 1; s.zf = (v >> 14) & 1; s.cf = (v >> 15) & 1
        elif op == 0x3d: s.PA = s.readop(s.pc()) & 0x1f; s.PC = s.A * 4; oc = 2; s.st = 1
        elif op == 0x3e: s.pio |= s.readop(s.pc()); s.incpc(); oc = 2; s.st = 1
        elif op == 0x3f: s.pio &= ~s.readop(s.pc()); s.incpc(); oc = 2; s.st = 1
        elif 0x40 <= op <= 0x43:
            a = s.read_r[0]() & 15; s.write_r[0](a | (1 << (op & 3))); s.st = 1
        elif 0x44 <= op <= 0x47:
            a = s.read_r[0]() & 15; s.write_r[0](a & ~(1 << (op & 3))); s.st = 1
        elif 0x48 <= op <= 0x4b:
            a = s.read_r[2]() & 15; s.st = 0 if (a & (1 << (op & 3))) else 1
        elif 0x4c <= op <= 0x4f: s.st = 0 if (s.A & (1 << (op & 3))) else 1
        elif 0x50 <= op <= 0x53:
            a = s.rd(op & 3); s.wr(op & 3, s.A); s.A = a; s.ZF_(s.A); s.st = 1
        elif 0x54 <= op <= 0x57:
            a = s.rd((op & 3) + 4); s.wr((op & 3) + 4, s.Y); s.Y = a; s.ZF_(s.Y); s.st = 1
        elif 0x58 <= op <= 0x5f: s.X = op & 7; s.ZF_(s.X); s.st = 1
        elif 0x60 <= op <= 0x67:
            a = s.readop(s.pc()); s.incpc(); oc = 2
            if s.st:
                s.SP[s.SI] = s.pc(); s.SI = (s.SI + 1) & 3
                s.PC = a & 0x3f; s.PA = ((op & 7) << 2) | (a >> 6)
            s.st = 1
        elif 0x68 <= op <= 0x6f:
            a = s.readop(s.pc()); s.incpc(); oc = 2
            if s.st:
                s.PC = a & 0x3f; s.PA = ((op & 7) << 2) | (a >> 6)
            s.st = 1
        elif 0x70 <= op <= 0x7f:
            a = (op & 15) + s.A; s.ST_C(a); s.cf = s.st ^ 1; s.A = a & 15; s.ZF_(s.A)
        elif 0x80 <= op <= 0x8f: s.Y = op & 15; s.ZF_(s.Y); s.st = 1
        elif 0x90 <= op <= 0x9f: s.A = op & 15; s.ZF_(s.A); s.st = 1
        elif 0xa0 <= op <= 0xaf:
            a = ((op & 15) - s.Y) & 0xff; s.CF_(a); a &= 15; s.ST_Z(a); s.zf = s.st ^ 1
        elif 0xb0 <= op <= 0xbf:
            a = ((op & 15) - s.A) & 0xff; s.CF_(a); a &= 15; s.ST_Z(a); s.zf = s.st ^ 1
        else:
            if s.st: s.PC = op & 0x3f
            s.st = 1
        s.cycles += oc
        s.update_pio()

    def run_until(s, cyc):
        while s.cycles < cyc:
            s.step()


# ======================================================================== アセンブラ
OPS = dict(nop=0x00, outO=0x01, outP=0x02, outR=0x03, tay=0x04, icy=0x08, icm=0x09, stic=0x0a, x=0x0b,
           rol=0x0c, ldm=0x0d, adc=0x0e, inK=0x12, inR=0x13, tya=0x14, dcy=0x18, dcm=0x19, xx=0x1b,
           ror=0x1c, stm=0x1d, sbc=0x1e, setc=0x21, rstc=0x23, tsti=0x25, tstc=0x28, tstz=0x29, rts=0x2c,
           eor=0x2f, rti=0x3c)
ARG4 = dict(tbit=(0x38, 3), xd=(0x50, 3), xyd=(0x54, 3), lxi=(0x58, 7),
            ldy=(0x80, 15), li=(0x90, 15), ci=(0xb0, 15), ai=(0x70, 15))
LONG = dict(jpl=0x68, call=0x60)


def assemble(prog):
    """prog: ('org',番地) ('label',名前) (命令, 引数) のリスト -> (1024バイト, ラベル表)"""
    addr = 0; labels = {}; items = []
    for it in prog:
        k = it[0]
        if k == 'org': addr = it[1]
        elif k == 'label': labels[it[1]] = addr
        else:
            items.append((addr, it)); addr += 2 if (k in LONG or k == 'en') else 1
    rom = bytearray(0x400)
    for a, it in items:
        k = it[0]
        if k in OPS: rom[a] = OPS[k]
        elif k in ARG4:
            base, mask = ARG4[k]; rom[a] = base | (it[1] & mask)
        elif k in LONG:
            t = labels[it[1]]; rom[a] = LONG[k] | (t >> 8); rom[a + 1] = t & 0xff
        elif k == 'en': rom[a] = 0x3e; rom[a + 1] = it[1]
        else: raise ValueError('未対応の命令: %s' % k)
    return bytes(rom), labels


# ======================================================================== 代替 54xx プログラム
def check_params(p):
    if len(p['level']) != 3 or any(not (0 <= v <= 15) for v in p['level']):
        raise ValueError('--level0/1/2 は 0〜15 で指定してください')
    if len(p['decay_div']) != 3 or any(not (1 <= v <= 16) for v in p['decay_div']):
        raise ValueError('--decay-div(0/1/2) は 1〜16 で指定してください')
    if len(p['decay_mode']) != 3 or any(v not in ('lin', 'exp') for v in p['decay_mode']):
        raise ValueError('--decay-mode は lin か exp を3つ(例 "lin,lin,exp")で指定してください')
    if not (1 <= p['seed'] <= 0xFFFF):
        raise ValueError('--seed は 0x0001〜0xFFFF で指定してください(0 は不可)')
    if not (0 <= p['pad_nops'] <= 60):
        raise ValueError('--pad-nops は 0〜60 で指定してください')
    for hi, ch in p['trigger'].items():
        if not (0 <= hi <= 15 and 0 <= ch <= 2):
            raise ValueError('--trigger は「上位4bit(0-15):出力(0-2)」の形式で指定してください')
    for hi, n in p['skip'].items():
        if not (0 <= hi <= 15 and 1 <= n <= 15):
            raise ValueError('--skip は「上位4bit(0-15):バイト数(1-15)」の形式で指定してください')
    if set(p['trigger']) & set(p['skip']):
        raise ValueError('--trigger と --skip で同じ上位4bitは使えません')
    for hi, lst in p.get('mix', {}).items():
        if not (0 <= hi <= 15) or hi in p['skip'] or not lst:
            raise ValueError('--mix の命令の上位4bit(0-15)が正しくないか、--skip と重なっています')
        for ch, lv in lst:
            if not (0 <= ch <= 2 and 0 <= lv <= 15):
                raise ValueError('--mix は「出力(0-2)=音量(0-15)」の形式で指定してください')


def actions(p):
    """命令の上位4bit -> [(出力, 鳴り始めの音量), ...]。--mix があれば --trigger/--level より優先。"""
    act = {hi: [(ch, p['level'][ch])] for hi, ch in p['trigger'].items()}
    for hi, lst in p.get('mix', {}).items():
        act[hi] = list(lst)
    return act


def program(p):
    check_params(p)
    P = []
    def a(*x): P.append(x)
    seed = p['seed']
    nib = [(seed >> (4 * i)) & 15 for i in range(4)]       # N0..N3
    a('org', 0);  a('jpl', 'main')                          # リセットベクタ
    a('org', 2);  a('jpl', 'irq')                           # 外部割り込みベクタ
    a('org', 0x10)
    a('label', 'main')
    a('lxi', 0)                                             # X=0 固定(以後、番地は Y だけで指定)
    for y, v in ((8, nib[0]), (9, nib[1]), (10, nib[2]), (11, nib[3]),
                 (12, 0), (13, 0), (14, 0), (15, 0), (2, 0), (3, 12),
                 (6, 16 - p['decay_div'][0]), (7, 16 - p['decay_div'][1]), (1, 16 - p['decay_div'][2])):
        a('ldy', y); a('li', v); a('stm')
    a('en', 0x04)                                           # 外部割り込み許可
    a('label', 'loop')
    # ---- 16bit ガロア LFSR を1ステップ(タップ 0xB400)
    a('rstc')
    for y in (11, 10, 9, 8):
        a('ldy', y); a('ldm'); a('ror'); a('stm')
    a('tstc'); a('jpl', 'noxor')
    a('li', 0xB); a('ldy', 11); a('eor'); a('stm')
    a('li', 0x4); a('ldy', 10); a('eor'); a('stm')
    a('label', 'noxor')
    # ---- 3つの出力: 値 = (乱数ビット ? 音量 : 0)
    for ch, (nbit_y, env_y) in enumerate(((8, 12), (9, 13), (10, 14))):
        a('ldy', nbit_y); a('tbit', 0); a('jpl', 'c%doff' % ch)
        a('ldy', env_y); a('ldm'); a('jpl', 'c%dout' % ch)
        a('label', 'c%doff' % ch); a('li', 0)
        a('label', 'c%dout' % ch)
        if ch == 0: a('rstc'); a('outO')
        elif ch == 1: a('setc'); a('outO')
        else: a('ldy', 1); a('outR')
    for _ in range(p['pad_nops']): a('nop')
    # ---- 減衰: 64ループごとの共通タイマーのあと、出力ごとに独立した分周カウンタで音量を1段階下げる
    divcell = (6, 7, 1)
    a('ldy', 2); a('icm'); a('jpl', 'loop')
    a('ldy', 3); a('icm'); a('jpl', 'loop')
    a('li', 12); a('ldy', 3); a('stm')                                   # 基準タイマーを64ループ周期に再設定
    for ch, env_y in enumerate((12, 13, 14)):
        a('ldy', divcell[ch]); a('icm'); a('jpl', 'e%dskip' % ch)        # この出力の分周がまだなら次へ
        a('li', 16 - p['decay_div'][ch]); a('ldy', divcell[ch]); a('stm')  # 分周カウンタを再設定
        a('ldy', env_y); a('ldm'); a('ci', 0); a('jpl', 'd%ddec' % ch); a('jpl', 'e%dskip' % ch)
        a('label', 'd%ddec' % ch)                                          # 音量が0でなければ1段階下げる
        if p['decay_mode'][ch] == 'lin':
            a('dcm')                                                       # 直線: 音量 - 1
        else:                                                              # 指数: 音量 - 切り上げ(音量÷4)
            a('ai', 3); a('ror'); a('rstc'); a('ror')                      #   A = (音量+3) >> 2
            a('rstc'); a('sbc'); a('stm')                                  #   音量 = 音量 - A
        a('label', 'e%dskip' % ch)
    a('li', 0); a('jpl', 'loop')
    # ---- 外部割り込み: 06XX から来る命令1バイトの処理
    a('label', 'irq')
    a('xd', 0); a('xyd', 0)                                 # A, Y を退避
    a('inK')                                                # A = K入力 = 命令の上位4bit
    a('ldy', 5); a('stm')
    a('ldy', 15); a('ldm'); a('ci', 0); a('jpl', 'fetching')
    a('ldy', 5); a('ldm')
    cmds = sorted([(hi, 'trig', lst) for hi, lst in actions(p).items()] +
                  [(hi, 'skip', n) for hi, n in p['skip'].items()])
    for i, (hi, kind, arg) in enumerate(cmds):
        last = (i == len(cmds) - 1)
        a('ci', hi); a('jpl', 'done' if last else 'nx%d' % i)     # 一致しなければ次の判定へ(最後は終了へ)
        if kind == 'trig':
            for ch, lv in arg:
                a('li', lv); a('ldy', 12 + ch); a('stm')                                 # 音量を設定
                a('li', 16 - p['decay_div'][ch]); a('ldy', divcell[ch]); a('stm')        # その出力の減衰カウンタを再設定
        else: a('li', arg); a('ldy', 15); a('stm')
        a('jpl', 'done')
        if not last: a('label', 'nx%d' % i)
    if not cmds: a('jpl', 'done')
    a('label', 'fetching'); a('ldy', 15); a('dcm')
    a('label', 'done')
    a('xyd', 0); a('xd', 0); a('rti')
    return P


def build(p):
    rom, labels = assemble(program(p))
    return rom, labels


# ======================================================================== FBNeo 風テスト環境
class Harness:
    """FBNeo の ボスコニアン 54xx 接続と同じ形で MCU を動かす(K=命令上位4bit, R0=下位4bit)。"""

    def __init__(h, rom):
        h.cpu = MB88(rom)
        h.latch = 0
        h.out = [0, 0, 0]
        h.log = []
        c = h.cpu
        c.read_k = lambda: h.latch >> 4
        c.read_r = [lambda: h.latch & 15, lambda: 0, lambda: 0, lambda: 0]

        def wo(v):
            ch = 1 if (v & 0x10) else 0
            h.out[ch] = v & 15; h.log.append((c.cycles, ch, v & 15))

        def wr1(v):
            h.out[2] = v & 15; h.log.append((c.cycles, 2, v & 15))
        c.write_o = wo
        c.write_r = [lambda v: None, wr1, lambda v: None, lambda v: None]

    def boot(h, cycles=3000): h.cpu.run_until(h.cpu.cycles + cycles)

    def send(h, byte, irq_cycles=40, gap=300):
        h.latch = byte
        h.cpu.set_irq(1); h.cpu.run_until(h.cpu.cycles + irq_cycles); h.cpu.set_irq(0)
        h.cpu.run_until(h.cpu.cycles + gap)

    def run(h, seconds): h.cpu.run_until(h.cpu.cycles + int(seconds * CYC_PER_SEC))


def bandpass_filters(rate):
    """FBNeo d_galaga.cpp の 54xx 出力フィルタ(3系統の多重帰還バンドパス)と同じ係数。"""
    R1 = [150000.0, 47000.0, 100000.0]; R2 = [22000.0, 10000.0, 22000.0]
    R3 = [470000.0, 150000.0, 220000.0]; R4 = [10000.0, 33000.0, 33000.0]
    C = [0.01e-6, 0.01e-6, 0.001e-6]
    r_min = min(R4); filt = []
    for i in range(3):
        r_in = R1[i] + 1.0 / (1.0 / 4700 + 1.0 / 10000 + 1.0 / 22000 + 1.0 / 47000)
        r1, r2, r3, c1, c2 = r_in, R2[i], R3[i], C[i], C[i]
        gain = r2 / (r1 + r2); rin = 1.0 / (1.0 / r1 + 1.0 / r2)
        fc = 1.0 / (2 * math.pi * math.sqrt(rin * r3 * c1 * c2))
        d = (c1 + c2) / math.sqrt(r3 / rin * c1 * c2)
        gain *= -r3 / rin * c2 / (c1 + c2)
        t2 = 2.0 * rate; t2s = t2 * t2
        w = rate * 2.0 * math.tan(math.pi * fc / rate); ws = w * w
        den = t2s + d * w * t2 + ws
        a1 = 2.0 * (-t2s + ws) / den; a2 = (t2s - d * w * t2 + ws) / den
        b0 = d * w * t2 / den
        g = r_min / R4[i]
        filt.append(dict(a1=a1, a2=a2, b0=b0 * gain * g, b2=-b0 * gain * g, fc=fc, x=[0, 0], y=[0, 0]))
    return filt


def render(h, rate=44100):
    """out[0..2] を、FBNeo と同じフィルタ・同じ加算で 16bit 波形にする。"""
    filt = bandpass_filters(rate)
    n = int(h.cpu.cycles / CYC_PER_SEC * rate)
    log = h.log; li = 0; cur = [0, 0, 0]; out = []
    for k in range(n):
        cyc = k * CYC_PER_SEC / rate
        while li < len(log) and log[li][0] <= cyc:
            cur[log[li][1]] = log[li][2]; li += 1
        tot = 0
        for i in range(3):
            f = filt[i]
            x0 = 4.0 / 15 * cur[i] - 2
            y0 = -f['a1'] * f['y'][0] - f['a2'] * f['y'][1] + f['b0'] * x0 + f['b2'] * f['x'][1]
            f['x'][1] = f['x'][0]; f['x'][0] = x0; f['y'][1] = f['y'][0]; f['y'][0] = y0
            tot += int(max(-2.0, min(1.5, y0)) * (16384 / 2) * 0.80)
        out.append(max(-32768, min(32767, tot)))
    return out


def write_wav(path, samples, rate=44100):
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
        w.writeframes(struct.pack('<%dh' % len(samples), *samples))


# ======================================================================== 特性測定・自己テスト
def measure(rom, labels, p):
    """ループ速度と、命令ごと・出力ごとの減衰時間(音量が0になるまで)を測る。"""
    h = Harness(rom); h.boot()
    c = h.cpu; L = labels['loop']; visits = []
    for _ in range(30000):
        if c.pc() == L: visits.append(c.cycles)
        c.step()
    d = [b - a for a, b in zip(visits, visits[1:])]
    avg = sum(d) / len(d)
    res = {}
    for hi, lst in sorted(actions(p).items()):
        h = Harness(rom); h.boot(); h.send(hi << 4)
        chans = [ch for ch, lv in lst if lv > 0]
        done = {}; t = 0.0
        while len(done) < len(chans) and t < 40:
            h.run(0.01); t += 0.01
            for ch in chans:
                if ch not in done and h.cpu.ram[12 + ch] == 0: done[ch] = t
        res[hi] = done
    return avg, CYC_PER_SEC / avg, res


def selftest(rom, labels, p):
    ok = True
    def report(name, good, detail=''):
        nonlocal ok
        print(('  [OK] ' if good else '  [NG] ') + name + (' ... ' + detail if detail else ''))
        ok = ok and good
    print('自己テスト:')
    act = actions(p)
    report('サイズが 1024 バイト', len(rom) == 1024)
    h = Harness(rom); h.boot(); h.run(0.2)
    report('起動直後は無音(出力0,0,0)・割り込み許可', h.out == [0, 0, 0] and h.cpu.pio == 4 and h.cpu.X == 0)
    for hi, lst in sorted(act.items()):
        h = Harness(rom); h.boot(); h.send(hi << 4); h.run(0.05)
        seen = [max([v for (_, c, v) in h.log if c == k], default=0) for k in range(3)]
        want = {ch for ch, lv in lst if lv > 0}
        good = all((seen[k] > 0) == (k in want) for k in range(3))
        report('命令 0x%Xn で出力 %s だけが鳴る' % (hi, sorted(want)), good, '各出力の最大値 %s' % seen)
    trig_hi = sorted(act)[0] if act else 1
    for hi, n in sorted(p['skip'].items()):
        h = Harness(rom); h.boot(); h.send(hi << 4)
        for i in range(n): h.send((trig_hi << 4) | 1)      # 設定バイトが発音命令に見えても鳴らないこと
        report('命令 0x%Xn のあとの %d バイトを読み飛ばす' % (hi, n),
               [h.cpu.ram[12], h.cpu.ram[13], h.cpu.ram[14]] == [0, 0, 0] and h.cpu.ram[15] == 0)
    # 出力ごとに減衰時間が独立して設定できる(出力0=4, 出力1=8, 出力2=16 → 約 0.8 : 1.6 : 3.3 秒)
    p2 = dict(p, level=[15, 15, 15], decay_div=[4, 8, 16], trigger={1: 0, 2: 1, 5: 2}, mix={}, decay_mode=['lin'] * 3)
    rom2, lab2 = build(p2)
    _, _, dec2 = measure(rom2, lab2, p2)
    t = [dec2[1][0], dec2[2][1], dec2[5][2]]
    exp = [15 * d * 0.01358 for d in (4, 8, 16)]
    report('出力ごとの減衰時間が独立している', all(abs(t[i] / exp[i] - 1) < 0.2 for i in range(3)),
           '出力0/1/2 = %.2f / %.2f / %.2f 秒(期待 %.2f / %.2f / %.2f)' % (tuple(t) + tuple(exp)))
    # 指数減衰: 音量が 15 → 11 → 8 → 6 → 4 → 3 → 2 → 1 → 0 と変化する
    p3 = dict(p, level=[15, 15, 15], decay_div=[3, 3, 3], trigger={1: 0, 2: 1, 5: 2}, mix={}, decay_mode=['exp'] * 3)
    rom3, lab3 = build(p3)
    h = Harness(rom3); h.boot(); h.send(0x50); seq = [h.cpu.ram[14]]
    for _ in range(400):
        h.run(0.005)
        if h.cpu.ram[14] != seq[-1]: seq.append(h.cpu.ram[14])
    report('指数減衰の音量が 15,11,8,6,4,3,2,1,0 と変化する', seq == [15, 11, 8, 6, 4, 3, 2, 1, 0], str(seq))
    # 割り込み連打でも乱数列が壊れない
    def ref(st):
        lsb = st & 1; st >>= 1
        return (st ^ 0xB400) if lsb else st
    h = Harness(rom); h.boot(); c = h.cpu; random.seed(1)
    prev = None; bad = 0; visits = 0; nxt = c.cycles + 100; off = 0; maxpc = 0
    for _ in range(400000):
        if c.pc() == labels['loop']:
            v = c.ram[8] | (c.ram[9] << 4) | (c.ram[10] << 8) | (c.ram[11] << 12)
            if prev is not None and v != ref(prev): bad += 1
            prev = v; visits += 1
        if c.cycles >= nxt:
            h.latch = random.randrange(256); c.set_irq(1)
            nxt = c.cycles + random.randrange(60, 400); off = c.cycles + random.randrange(5, 50)
        if off and c.cycles >= off: c.set_irq(0); off = 0
        c.step(); maxpc = max(maxpc, c.pc())
    used = max(i for i, b in enumerate(rom) if b) + 1          # プログラムの末尾(これを超えて実行したら暴走)
    report('ランダム命令の連打でも乱数列が崩れない', bad == 0 and c.X == 0 and maxpc < used,
           '周回 %d 回, 不一致 %d, 最大PC 0x%X' % (visits, bad, maxpc))
    print('結果: ' + ('すべて OK' if ok else '失敗があります'))
    return ok


# ======================================================================== コマンドライン
def parse_map(text, name):
    d = {}
    try:
        for part in text.split(','):
            k, v = part.split(':'); d[int(k, 0)] = int(v, 0)
    except Exception:
        raise ValueError('%s は "1:0,2:1" の形式で指定してください' % name)
    return d


def parse_mix(text):
    mix = {}
    try:
        for part in text.split(';'):
            if not part.strip(): continue
            hi, rest = part.split(':'); lst = []
            for it in rest.split(','):
                ch, lv = it.split('='); lst.append((int(ch, 0), int(lv, 0)))
            mix[int(hi, 0)] = lst
    except Exception:
        raise ValueError('--mix は "1:0=15,1=7;2:1=15" の形式で指定してください')
    return mix


def main():
    ap = argparse.ArgumentParser(
        description='ボスコニアン用 代替 54xx.bin(MB8844)作成ツール。詳しい説明はこのファイル先頭のコメントを参照。',
        formatter_class=argparse.RawDescriptionHelpFormatter)
    D = DEFAULTS
    for i, nm in enumerate(('出力0(低い「ゴォー」)', '出力1(中音)', '出力2(「ザー」)')):
        ap.add_argument('--level%d' % i, type=int, default=None, help='%sの鳴り始めの音量 0-15 (既定 15)' % nm)
    ap.add_argument('--decay-div', type=int, default=None, help='3つの出力の減衰の遅さをまとめて指定 1-16 (個別指定が優先)')
    for i in range(3):
        ap.add_argument('--decay-div%d' % i, type=int, default=None, help='出力%dの減衰の遅さ 1-16。大きいほどゆっくり消える (既定 8 = 約1.6秒)' % i)
    ap.add_argument('--decay-mode', default=None, help='出力ごとの減衰の形。lin=直線 / exp=指数(キレ・アタック感)。例 "lin,lin,exp" (既定 すべて lin)')
    ap.add_argument('--seed', type=lambda s: int(s, 0), default=D['seed'], help='乱数の初期値(16bit, 0以外) (既定 0xC3A5)')
    ap.add_argument('--pad-nops', type=int, default=D['pad_nops'], help='ループに足す nop の数 0-60。増やすとこもった音になる (既定 0)')
    ap.add_argument('--trigger', default=','.join('%d:%d' % kv for kv in D['trigger'].items()),
                    help='命令の上位4bit:鳴らす出力 の対応 (既定 "1:0,2:1,5:2")')
    ap.add_argument('--mix', default=None, help='1つの命令で複数の出力を鳴らす。例 "1:0=15,1=7,2=7;2:0=11,1=15"')
    ap.add_argument('--skip', default=','.join('%d:%d' % kv for kv in D['skip'].items()),
                    help='命令の上位4bit:続く設定バイト数 の対応 (既定 "3:4,4:4,6:5")')
    ap.add_argument('--out', default='54xx.bin', help='出力ファイル名 (既定 54xx.bin)')
    ap.add_argument('--into-zip', metavar='ZIP', help='指定した zip の中の 54xx.bin を差し替える(元は ZIP名.bak に保存)')
    ap.add_argument('--test', action='store_true', help='自己テストを実行する')
    ap.add_argument('--info', action='store_true', help='ループ速度と減衰時間を表示する')
    ap.add_argument('--preview', metavar='DIR', help='確認用の WAV を DIR に書き出す(FBNeo と同じフィルタを通した音)')
    args = ap.parse_args()
    try:
        p = dict(level=list(D['level']), decay_div=list(D['decay_div']), seed=args.seed, pad_nops=args.pad_nops,
                 trigger=parse_map(args.trigger, '--trigger'), skip=parse_map(args.skip, '--skip'), mix=dict(D['mix']),
                 decay_mode=list(D['decay_mode']))
        if args.decay_div is not None: p['decay_div'] = [args.decay_div] * 3
        for i in range(3):
            v = getattr(args, 'decay_div%d' % i)
            if v is not None: p['decay_div'][i] = v
            v = getattr(args, 'level%d' % i)
            if v is not None: p['level'][i] = v
        if args.mix is not None: p['mix'] = parse_mix(args.mix)
        if args.decay_mode is not None:
            dm = [t.strip() for t in args.decay_mode.split(',')]
            p['decay_mode'] = dm * 3 if len(dm) == 1 else dm
        rom, labels = build(p)
    except ValueError as e:
        print('エラー: %s' % e); return 2
    with open(args.out, 'wb') as f: f.write(rom)
    used = max(i for i, b in enumerate(rom) if b) + 1
    print('作成しました: %s (%d バイト, プログラム部分 %d バイト)' % (args.out, len(rom), used))
    if args.into_zip:
        shutil.copy(args.into_zip, args.into_zip + '.bak')
        with zipfile.ZipFile(args.into_zip + '.bak') as zi, zipfile.ZipFile(args.into_zip, 'w', zipfile.ZIP_DEFLATED) as zo:
            names = [i.filename for i in zi.infolist()]
            for it in zi.infolist(): zo.writestr(it.filename, rom if it.filename == '54xx.bin' else zi.read(it.filename))
            if '54xx.bin' not in names: zo.writestr('54xx.bin', rom)
        print('zip を更新しました: %s (元のファイルは %s.bak)' % (args.into_zip, args.into_zip))
    if args.info:
        avg, rate, res = measure(rom, labels, p)
        print('ノイズの更新: 1ループ平均 %.1f サイクル → 約 %d Hz' % (avg, round(rate)))
        for hi, lst in sorted(actions(p).items()):
            desc = ', '.join('出力%d=%d(%.2f秒)' % (ch, lv, res[hi].get(ch, 0)) for ch, lv in lst)
            print('  命令 0x%Xn → %s' % (hi, desc))
    if args.test:
        if not selftest(rom, labels, p): return 1
    if args.preview:
        os.makedirs(args.preview, exist_ok=True)
        act = actions(p)
        cases = [('all_commands', [(hi << 4) for hi in sorted(act)])]
        cases += [('cmd_0x%X0' % hi, [hi << 4]) for hi in sorted(act)]
        for name, seq in cases:
            h = Harness(rom); h.boot()
            for b in seq: h.send(b)
            h.run(3.0)
            wav = render(h); path = os.path.join(args.preview, '54xx_%s.wav' % name)
            write_wav(path, wav)
            print('  確認用WAV: %s (最大振幅 %d)' % (path, max(abs(v) for v in wav)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
