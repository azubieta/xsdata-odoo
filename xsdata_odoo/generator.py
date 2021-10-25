import os
from pathlib import Path
from typing import Iterator
from typing import List

from jinja2 import Environment
from jinja2 import FileSystemLoader
from xsdata.codegen.models import Class
from xsdata.codegen.resolver import DependenciesResolver
from xsdata.formats.mixins import AbstractGenerator
from xsdata.formats.mixins import GeneratorResult
from xsdata.models.config import GeneratorConfig


class OdooGenerator(AbstractGenerator):
    """Odoo generator."""

    def __init__(self, config: GeneratorConfig):
        super().__init__(config)
        tpl_dir = Path(__file__).parent.joinpath("templates")
        self.env = Environment(loader=FileSystemLoader(str(tpl_dir)), autoescape=False)

    def render(self, classes: List[Class]) -> Iterator[GeneratorResult]:
        """Return a iterator of the generated results."""
        packages = {obj.qname: obj.target_module for obj in classes}
        resolver = DependenciesResolver(packages=packages)

        for module, cluster in self.group_by_module(classes).items():
            yield GeneratorResult(
                path=module.with_suffix(".py"),
                title=cluster[0].target_module,
                source=self.render_module(resolver, cluster),
            )

    def render_module(
        self, resolver: DependenciesResolver, classes: List[Class]
    ) -> str:
        """Render the source code for the target module of the given class
        list."""
        resolver.process(classes)
        output = self.render_classes(resolver.sorted_classes())
        output = self.env.get_template("module.jinja2").render(output=output)
        return f"{output}\n"

    def render_classes(self, classes: List[Class]) -> str:
        """Render the source code of the classes."""
        load = self.env.get_template
        classes = sorted(classes, key=lambda x: x.name)
        schema = os.environ.get("SCHEMA", "")
        # print("SCHEMA", schema)
        version = os.environ.get("VERSION", "")
        # print("VERSION", version)
        field_prefix = f"{schema}{version}_"
        # print("field_prefix", field_prefix)

        def render_class(obj: Class) -> str:
            """Render class or enumeration."""
            template = "enum.jinja2" if obj.is_enumeration else "class.jinja2"
            return load(template).render(obj=obj, field_prefix=field_prefix).strip()

        output = "\n\n".join(map(render_class, classes))
        return f"\n{output}\n"
