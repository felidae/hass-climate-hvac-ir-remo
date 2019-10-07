Home Assistant platform for Nature Remo Local API
==========

Nature Remo Local APIを利用したHome Assistantのエアコンコンポーネントです。

エアコン(climate)コンポーネントとして合成したリモコン信号を送信します。

## 注意事項

- 自家用に作ったものです。
- 各方面に非公式です。
- Docker環境のhass.ioで動作を確認しました。
- daikin2の信号を[Remo](https://nature.global/)と
  [Remo互換の信号を受け付けるIRKitクローン](https://github.com/toskaw/ESP8266IRKit)で試しています。

## 試し方

- `custom_components/hvac_ir`フォルダにファイルを配置する
- `https://github.com/shprota/hvac_ir/tree/master/hvac_ir`を参考にエアコンのタイプを選ぶ
  - e.g. daikin2, fujitsu
- `configuration.yaml`に以下の例のように書き加える
- `device:`をirkitにするとIRKitで動作する信号を送信する

```
climate:
  - platform: hvac_ir
    name: Set your HVAC name.
    host: <Nature Remo IP>
    type: <HVAC model type>
    device: remo/irkit
```
- hassを再起動する
