"""Test utilities: load functions out of streamlit_app.py via AST.

The app is a Streamlit script — importing it directly would execute
Streamlit calls (st.set_page_config, etc.). Instead we parse the file,
extract the requested top-level function definitions (stripping decorators
like @st.cache_data), and exec them in an isolated namespace with the
stdlib/third-party imports they need.

Transitive dependencies are resolved automatically: if an extracted
function calls another top-level function from the app, that function is
extracted too (fixpoint, up to _MAX_DEPTH rounds).
"""
import ast
import pathlib

APP_PATH = pathlib.Path(__file__).resolve().parent.parent / "streamlit_app.py"
_MAX_DEPTH = 12


def _base_namespace():
    import re
    import html
    import json
    from difflib import SequenceMatcher

    ns = {"re": re, "html": html, "json": json, "SequenceMatcher": SequenceMatcher}
    try:
        from bs4 import BeautifulSoup
    except ImportError:  # pragma: no cover
        BeautifulSoup = None
    ns["BeautifulSoup"] = BeautifulSoup
    return ns


def _unresolved_names(node, ns):
    """Names a function body references that aren't params, builtins, or in ns."""
    import builtins

    param_names = {a.arg for a in list(node.args.args) + list(node.args.kwonlyargs)}
    if node.args.vararg:
        param_names.add(node.args.vararg.arg)
    if node.args.kwarg:
        param_names.add(node.args.kwarg.arg)
    assigned = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Store):
            assigned.add(child.id)
        elif isinstance(child, ast.ExceptHandler) and child.name:
            # 'except Exception as e:' binds e, but not via ast.Name(Store)
            assigned.add(child.name)
        elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            assigned.add(child.name)
        elif isinstance(child, ast.Lambda):
            # lambda params never appear as ast.Name(Store)
            for a in list(child.args.args) + list(child.args.kwonlyargs):
                assigned.add(a.arg)
            if child.args.vararg:
                assigned.add(child.args.vararg.arg)
            if child.args.kwarg:
                assigned.add(child.args.kwarg.arg)
    builtin_names = set(dir(builtins))
    used = {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}
    return sorted(
        n
        for n in used
        if n not in param_names
        and n not in assigned
        and n not in ns
        and n not in builtin_names
    )


def _is_literal_value(node):
    """True for AST values safe to exec without side effects."""
    if isinstance(node, ast.Constant):
        return True
    if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        return all(_is_literal_value(e) for e in node.elts)
    if isinstance(node, ast.Dict):
        return all(
            _is_literal_value(k) and _is_literal_value(v)
            for k, v in zip(node.keys, node.values)
        )
    if isinstance(node, ast.UnaryOp) and isinstance(
        node.op, (ast.UAdd, ast.USub, ast.Not, ast.Invert)
    ):
        return _is_literal_value(node.operand)
    return False


def load_functions(*names):
    """Return {name: function} for top-level defs in streamlit_app.py.

    Raises AssertionError with a clear message if a function (or one of its
    transitive callees) references a module-level global that isn't available
    (e.g. a compiled regex constant or st). Either add it to the namespace
    here or refactor the function to take it as a parameter.
    """
    src = APP_PATH.read_text(encoding="utf-8")
    tree = ast.parse(src)
    defs = {
        n.name: n
        for n in tree.body
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    # Simple module-level constants (e.g. STRICT_CVS_VARIANT_MATCH = True)
    # that extractors may reference.
    assigns = {}
    for n in tree.body:
        if (
            isinstance(n, ast.Assign)
            and len(n.targets) == 1
            and isinstance(n.targets[0], ast.Name)
            and _is_literal_value(n.value)
        ):
            assigns[n.targets[0].id] = n
    ns = _base_namespace()
    seen = set()
    loaded_nodes = {}
    pending = list(names)
    depth = 0
    while pending and depth < _MAX_DEPTH:
        depth += 1
        nxt = []
        for name in pending:
            if name in seen:
                continue
            seen.add(name)
            node = defs.get(name)
            if node is None:
                raise AssertionError(
                    f"no top-level function {name!r} in {APP_PATH.name}"
                )
            node.decorator_list = []  # drop e.g. @st.cache_data
            loaded_nodes[name] = node
            code = compile(
                ast.Module(body=[node], type_ignores=[]), str(APP_PATH), "exec"
            )
            exec(code, ns)
            for child in ast.walk(node):
                if not isinstance(child, ast.Name):
                    continue
                callee = child.id
                if callee not in ns and callee in defs and callee not in seen:
                    nxt.append(callee)
        pending = nxt

    # Pull in literal module-level constants referenced by loaded functions.
    for _ in range(5):
        progressed = False
        for node in list(loaded_nodes.values()):
            for m in _unresolved_names(node, ns):
                if m in ns or m in defs:
                    continue
                anode = assigns.get(m)
                if anode is None:
                    continue
                code = compile(
                    ast.Module(body=[anode], type_ignores=[]), str(APP_PATH), "exec"
                )
                exec(code, ns)
                progressed = True
        if not progressed:
            break

    # Report anything still unresolved, across ALL loaded functions
    # (not just the requested ones — transitive callees count too).
    problems = {}
    for name, node in loaded_nodes.items():
        missing = [
            m for m in _unresolved_names(node, ns) if m not in defs
        ]
        if missing:
            problems[name] = missing
    if problems:
        detail = "; ".join(f"{f} needs {g}" for f, g in problems.items())
        raise AssertionError(
            f"functions reference module-level globals not available in tests: {detail}. "
            "Add them to _base_namespace() in conftest.py or refactor to parameters."
        )
    return {n: ns[n] for n in names}
