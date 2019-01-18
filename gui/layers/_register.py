import re
import inspect

from ..elements import Viewer


template = """def {name}(self, {signature}):
    layer = {cls_name}({call_args})
    self.add_layer(layer)
    return layer
"""

pattern = re.compile(r'(.)([A-Z][a-z]+)')


def camel_to_snake(name):
    # https://gist.github.com/jaytaylor/3660565
    return pattern.sub(r'\1_\2', name).lower()


class CallDefault(inspect.Parameter):
    def __str__(self):
        kind = self.kind
        formatted = self._name

        # Fill in defaults
        if self._default is not inspect._empty:
            formatted = '{}={}'.format(formatted, formatted)

        if kind == inspect._VAR_POSITIONAL:
            formatted = '*' + formatted
        elif kind == inspect._VAR_KEYWORD:
            formatted = '**' + formatted

        return formatted


class CallSignature(inspect.Signature):
    _parameter_cls = CallDefault


def create_func(cls, name=None, doc=None):
    module = inspect.getmodule(cls)

    module_name = module.__name__
    cls_name = cls.__name__
    sig = inspect.signature(cls)
    call_args = CallSignature.from_callable(cls)

    if name is None:
        name = camel_to_snake(cls_name)

    if 'layer' in name:
        raise ValueError(f"name {name} should not include 'layer'")

    name = 'add_' + name

    if doc is None:
        doc = inspect.getdoc(cls)
        cutoff = doc.find('\n\nParameters\n----------\n')
        if cutoff > 0:
            doc = doc[cutoff:]

        n = 'n' if cls_name[0].lower() in 'aeiou' else ''
        doc = f'Adds a{n} {cls_name} layer to the viewer. ' + doc
        doc += '\n\nReturns\n-------\n'
        doc += f'layer : {module_name}.{cls_name}'
        doc += '\n\tAdded layer.'
        doc = doc.expandtabs(4)

    src = template.format(name=name,
                          signature=str(sig)[1:-1],
                          cls_name=cls_name,
                          call_args=str(call_args)[1:-1])

    execdict = {cls_name: cls}
    exec(src, execdict)
    func = execdict[name]

    func.__doc__ = doc

    return func


def _register(cls, *, name=None, doc=None):
    func = create_func(cls, name=name, doc=doc)
    setattr(Viewer, func.__name__, func)
    return cls


def add_to_viewer(cls=None, *, name=None, doc=None):
    """Adds a layer creation convenience method under viewers
    as ``add_{name}``.

    Parameters
    ----------
    cls : type, optional
        Class to register.
        If None, this function is treated as a decorator.
    name : string, keyword-only
        Name in snake-case of the layer name.
        If None, is autogenerated from the class name.
    doc : string, keyword-only
        Docstring to use in the method.
        If None, is autogenerated from the existing docstring.
    """
    if cls is not None:
        return _register(cls, name=name, doc=doc)

    def inner(cls):
        return _register(cls, name=name, doc=doc)
