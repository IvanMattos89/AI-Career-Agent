"""One Qt application with deterministic teardown before interpreter shutdown."""
import gc
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="session", autouse=True)
def qt_application_lifetime():
    from PySide6.QtCore import QCoreApplication, QEvent
    from PySide6.QtWidgets import QApplication
    from shiboken6 import delete

    application = QApplication.instance() or QApplication([])
    yield application
    application.closeAllWindows()
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    application.processEvents()
    gc.collect()
    # Destroy C++ resources while Python/Qt modules are still alive.
    delete(application)


@pytest.fixture(autouse=True)
def qt_widget_lifetime(qt_application_lifetime):
    from PySide6.QtCore import QCoreApplication, QEvent

    yield
    for widget in qt_application_lifetime.topLevelWidgets():
        widget.close()
        widget.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    qt_application_lifetime.processEvents()
    gc.collect()
