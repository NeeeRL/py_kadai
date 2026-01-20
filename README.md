# py_kadai

## 使い方
ドッカーをインストールします。 ここでは割愛します。ただし、ローカルにpython実行環境があるなら、ドッカーの使い方は見ずに、./optのディレクトリに移動してください

## ドッカーの使い方
### コンテナの起動
```bash
docker compose up -d --build
```
### コンテナの起動(ネットワークなしに)
```bash
docker compose up -d
```
### コンテナにはいる
```bash
docker exec -it py-python-app-1 /bin/bash
```
### コンテナのストップ
```bash
docker compose stop
```

dockerのセットアップが終われば私の設定した、nvimが使えるはずです。Masonを使ってLSPを入れてください。わかっているとは思いますが、別にこの環境は汚しても構わないので、仮想環境を使用してpip installする必要はほぼないです。グラフィカルに確かめるには、vnc://localhost:5905にアクセスしてください。5905が使用中の場合は、docker-compose.ymlを編集して、ポートフォアチングを自身で行ってください。

## nvimの使用方法
とりあえずpython以外でも使っているので、なんとも言えませんが、最低限見るためだけのコマンドを書いておきます。(クローン元のreadmeにはほとんど書いてないので) できるだけLazyに近づけたので、そこの部分は割愛します。

### バッファを閉じる
<space + w> を使用します。
### Neo-treeを閉じる
<space + e> を使用します
### pythonなどの実行
<space + r> を実行します。python以外でも使用できますが、pyファイルを開いているなら、自動的にやってくれるので便利です。

ここまで終われば、スクリプトの実行へ進んでください

## ローカルで行う場合
### 作業ディレクトリへ
```bash
cd opt
```
を実行してください。カレントディレクトリがファイルのすぐ親になることができます。
### pythonの実行環境を整える
Ubuntuの場合、以下のコマンドでPythonとpip、そしてpygameをインストールします。

```bash
sudo apt update
sudo apt install -y python3 python3-pip
pip install pygame
```

### スクリプトの実行
optディレクトリに移動し、以下のコマンドでゲームを実行します。

```bash
cd opt
python3 pazmon.py
```

## ライブラリの入れ方
```
source venv/bin/activate
pip install LIBRARY
```
