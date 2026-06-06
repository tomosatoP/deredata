# テスト エクスプローラー

やっぱり、**単体テストのテスト検出エラー**。
コマンドラインで手入力。

~~~sh
coverage run -m unittest discover -v -s tests -p test_*.py -t tests
coverage report # もしくは、 "coverage html"
~~~
