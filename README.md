# デレステスコア計算アプリ（未完成）

感謝：[デレステ攻略Wiki](https://gamerch.com/imascg-slstage-wiki/)（アイドル、アイドルのエピソード、スコア計算方法など多岐）を参考にした。

**手持ち** のアイドルで最適なユニットを編成するツールが欲しくて作成した。
スコア計算に特化してるので、放置編成やファン数稼ぎ編成には不向きだと思う。

## 機能

### ユニット編成

#### アイドル（エピソード）の個別指定

アイドル（エピソード）を1人ずつユニットに配置し、ユニットを編成する。

#### アイドルのセンター効果および特技による複数選択

センター効果および特技で絞り込んだアイドル（エピソード）をユニットに配置し、ユニットを編成する。

### スコア計算

楽曲とユニットを選んで、スコア計算を行う。

### アイドル編集

アイドルのポテンシャル値（ボーカル、ダンス、ビジュアル、ライフ、特技）を編集する。
手間なので、ポテンシャル値の未割当分は考慮しない。

## アイドル（エピソード）編集

アイドル（エピソード）のスターランクを編集する。
特技レベル、親愛度、レベルは、特訓済みの最大値を適用する。
したがって、特訓前は考慮しない。

## マイスタイルアイドル（エピソード）編集

思案中。

## インストール手順

WSL2 ubuntu 環境で動作します。

### 前準備

Python仮想環境を用意する。

~~~shell
mkdir deredata
cd deredata

python -m venv venv --upgrade-deps
~~~

### インストール

~~~shell
cd derenotes

. venv/bin/activate
pip install git+https://github.com/tomosatoP/deredata.git
init
~~~

### アップデート

~~~shell
cd derenotes

. venv/bin/activate
pip install -U git+https://github.com/tomosatoP/deredata.git
~~~

## 使い方

~~~shell
cd deredata

. venv/bin/activate
python -m deredata
~~~

-----

## 参考資料

[kivy RecycleView](recycleview.md)
[kivy asincio](kivy.asyncio.md)
