# API ドキュメントの作り方

`Sphinx`でPythonモジュールのAPIドキュメントWebページを作成する。
Pythonモジュールに記述された`docstring`の内容に基づいて作成される。

## 準備

`Sphinx`のインストール＆初期設定。

~~~shell
pip install sphinx

sphinx-quickstart docs/api
... 選択されたルートパス: docs/api
... > ソースディレクトリとビルドディレクトリを分ける（y / n） [n]: y
... > プロジェクト名: derenotes
... > 著者名（複数可）: tomosatoP
... > プロジェクトのリリース []: 1.0.0
... > プロジェクトの言語 [en]: ja
~~~

> [!NOTE]
> 事前に`locale`設定の`LC_ALL`を確認し、未設定なら設定しておく。
> Python仮想環境での実行がお勧め。

`docs/api`フォルダが作成され、その配下に作成されるファイル群。

- source/conf.py
- source/index.rst
- Makefile
- make.bat

### 動作確認

まずは、Webページが表示されるようになったことを確認する。

~~~shell
sphinx-build -M html docs/api/source docs/api/build
chrome docs/api/build/html/index.html
~~~

## Webページのカスタマイズ

定義ファイルとマスターファイルを編集し、Webページを完成させる。

### 定義ファイルの編集

`docs/api/source/conf.py`

~~~diff
@@ -14,15 +14,42 @@
 # -- General configuration ---------------------------------------------------
 # https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration
 
-extensions = []
+extensions = [
+    "sphinx.ext.apidoc",
+    "sphinx.ext.autodoc",
+    "sphinx.ext.autosummary",
+    "sphinx.ext.todo",
+    "sphinx.ext.githubpages",
+]
+
+apidoc_modules = [
+    {
+        "path": "../../../deredata",
+        "destination": "modules",
+        "max_depth": 2,
+        "separate_modules": True,
+        "module_first": True,
+        "implicit_namespaces": True,
+        "automodule_options": {
+            "members",
+            "show-inheritance",
+            "undoc-members",
+        },
+    },
+]
+
+add_module_names = False
+autoclass_content = "both"
+autodoc_member_order = "bysource"
+autodoc_typehints = "description"
 
 templates_path = ["_templates"]
-exclude_patterns = []
+exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]
 
 language = "ja"
 
 # -- Options for HTML output -------------------------------------------------
 # https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output
 
-html_theme = "alabaster"
+html_theme = "nature"
 html_static_path = ["_static"]
~~~

### マスターファイルの編集

`docs/api/source/index.rst`

~~~diff
@@ -1,17 +1,15 @@
 .. derenotes documentation master file, created by
-   sphinx-quickstart on *** *** ** **:**:** ****.
+   sphinx-quickstart on *** *** ** **:**:** ****.
    You can adapt this file completely to your liking, but it should at least
    contain the root `toctree` directive.
 
 derenotes documentation
 =======================
 
-Add your content using ``reStructuredText`` syntax. See the
-`reStructuredText <https://www.sphinx-doc.org/en/master/usage/restructuredtext/index.html>`_
-documentation for details.
-
-
 .. toctree::
    :maxdepth: 2
    :caption: Contents:
 
+   modules/modules
+   modules/deredata.libs
~~~

## Webページの作成

作成する。

~~~shell
sphinx-build -M html docs/api/source docs/api/build
chrome docs/api/build/html/index.html
~~~

### 作り直し

設定ファイルやマスターファイルなどを変更したら、作り直す。

~~~shell
sphinx-build -M clean docs/api/source docs/api/build
sphinx-build -M html docs/api/source docs/api/build
chrome docs/api/build/html/index.html
~~~

---
差分テキストの作り方

~~~shell
diff -u 変更前のテキストファイル 変更後のテキストファイル
~~~
