from labelle.gui.gui import LabelleWindow
from labelle.gui.q_label_widgets import (
    TextDymoLabelWidget,
)


def test_main_window(qtbot):
    widget = LabelleWindow()
    qtbot.addWidget(widget)

    assert not widget._actions.isEnabled()
    assert widget._device_selector.isEnabled()
    assert not widget._label_list.isEnabled()
    assert not widget._render_widget.isEnabled()
    assert not widget._render.isEnabled()
    assert not widget._settings_toolbar.isEnabled()
    assert widget._device_selector._error_label.text() == "No supported devices found"
    assert not widget._actions._print_button.isEnabled()
    assert widget._label_list.count() == 1
    item = widget._label_list.itemWidget(widget._label_list.item(0))
    assert isinstance(item, TextDymoLabelWidget)
    assert item.label.toPlainText() == "text"
