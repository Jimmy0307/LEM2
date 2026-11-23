# Adapter 範例（不是 PRISM）

先安裝研究平台 Wheel，再執行 `pip install ./examples/lookup_adapter`。

套件會註冊 `[project.entry-points."federated_decision_making.algorithms"]`，接著 `fdm algorithms` 可自動找到 `lookup_example`，`fdm run` 參數 `algorithm` 換成 `lookup_example` 即可。

實際 PRISM／RIPPER／DRSA Adapter 應按照相同 API 撰寫，**需要真實演算法原理與相同測試集**，不要直接將此 Lookup 範例冒充為其算法。
