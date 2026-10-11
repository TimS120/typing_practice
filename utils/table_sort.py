"""Sortable table headings with a single, unambiguous direction indicator."""


def indicate_sort(table, column, descending):
    if not hasattr(table, "_heading_labels"):
        table._heading_labels = {name: table.heading(name, "text") for name in table["columns"]}
    for name, label in table._heading_labels.items():
        arrow = (" ↓" if descending else " ↑") if name == column else ""
        table.heading(name, text=label + arrow)


def sort_table(table, column, descending=None):
    if descending is None:
        descending = getattr(table, "_sort_column", None) == column and not getattr(table, "_sort_reverse", False)
    table._sort_column, table._sort_reverse = column, descending

    def key(item):
        value = table.set(item, column)
        try:
            return 0, float(value.rstrip("%"))
        except ValueError:
            return 1, value

    for index, item in enumerate(sorted(table.get_children(), key=key, reverse=descending)):
        table.move(item, "", index)
    indicate_sort(table, column, descending)
