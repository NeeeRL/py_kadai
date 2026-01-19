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

