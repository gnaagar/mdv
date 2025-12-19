# Index of {{ root }}{{ '\n\n' }}
{%- macro render(node, depth=0) -%}
{%- set pad = '  ' * depth -%}
{%- if node.type == 'directory' -%}
{{ pad }}- [{{ node.name }}](/{{ path }}/{{ node.path }}){{ '\n' }}
{%- for child in node.children -%}
{{ render(child, depth + 1) }}
{%- endfor -%}
{%- else -%}
{{ pad }}- [{{ node.name }}](/{{ path }}/{{ node.path }}){{ '\n' }}
{%- endif -%}
{%- endmacro -%}

{%- for item in tree -%}
{{ render(item) }}
{%- endfor -%}
