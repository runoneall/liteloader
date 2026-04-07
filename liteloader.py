import importlib.util
import os
from pathlib import Path
from types import SimpleNamespace


class _Framer:
    # 模块必须通过 self.framer 访问 framer 对象
    # 模块逻辑必须通过命名空间动态调用防止闭包陷阱导致注入失效
    framer = SimpleNamespace()

    # 模块必须位于和 liteloader.py 同级的 modules 目录下
    _modules_dir = Path(__file__).parent / "modules"

    def __init__(self):
        if not self._modules_dir.exists():
            self._modules_dir.mkdir()

        # liteloader 会自动加载 modules 目录下的模块
        self._load_all()

    _loaded_modules: set[str] = set()

    # 模块必须使用 self._require 来声明依赖
    # name 必须是 modules 目录下的文件名或目录名
    # 如果模块是文件必须包含 .py 后缀
    def _require(self, name: str):
        if name in self._loaded_modules:
            return

        # 模块形式必须是文件或目录
        # 目录形式模块必须包含 __init__.py 文件
        # 必须优先使用目录形式模块
        # 如果逻辑简单使用文件形式模块
        base_path = self._modules_dir / name
        module_path = base_path / "__init__.py" if base_path.is_dir() else base_path

        if not module_path.exists():
            raise ModuleNotFoundError(
                f"liteloader: module '{name}' not found at {module_path}"
            )

        spec = importlib.util.spec_from_file_location(name, module_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"liteloader: failed to load module spec for '{name}'")

        module = importlib.util.module_from_spec(spec)
        module.__dict__["Framer"] = _Framer  # 模块必须继承 Framer 类
        spec.loader.exec_module(module)

        # 模块必须要有 Module 类
        # 必须在 Module 类的同一行加入注释 # type: ignore
        if not hasattr(module, "Module"):
            raise AttributeError(
                f"liteloader: module '{name}' missing 'Module' class definition"
            )

        module.Module()  # 模块必须在 __init__ 中执行初始化逻辑
        self._loaded_modules.add(name)

    # 模块必须创建一个命名空间承载暴露的 api
    # 必须使用 self.namespace = self._namespace("space_name") 来创建命名空间
    # 注入型模块不需要这一步
    # 注入型模块必须通过 self.framer.space_name 访问其他模块命名空间
    def _namespace(self, name: str) -> SimpleNamespace:
        namespace = SimpleNamespace()
        setattr(self.framer, name, namespace)
        return namespace

    def _load_all(self):
        for item in os.listdir(self._modules_dir):
            if not item.startswith("_"):  # 自动忽略以 _ 开头的文件或目录
                self._require(item)


# 业务逻辑必须使用 from liteloader import framer 引入 framer 对象
# 模块逻辑禁止从 liteloader 导入任何对象
# 业务逻辑必须通过 framer.space_name 访问其他模块命名空间
framer = _Framer().framer
