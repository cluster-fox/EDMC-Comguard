import semantic_version

from comguard.comguard import Comguard

PLUGIN_NAME = "EDMC-Comguard"
PLUGIN_VERSION = semantic_version.Version.coerce("3.0.1")

# Initialise the main plugin class
this = Comguard(PLUGIN_NAME, PLUGIN_VERSION)

#Direct calls on : comguard.Ui, comguard.plugin_name, comguard.state


def plugin_start3(plugin_dir):
    """
    Load this plugin into EDMC
    """
    this.plugin_start(plugin_dir)

    return this.plugin_name


def plugin_stop():
    """
    EDMC is closing
    """
    this.plugin_stop()


def plugin_app(parent):
    """
    Return a TK Frame for adding to the EDMC main window
    """
    return this.Ui.get_plugin_frame(parent)


def plugin_prefs(parent, cmdr: str, is_beta: bool):
    """
    Return a TK Frame for adding to the EDMC settings dialog
    """
    return this.Ui.get_prefs_frame(parent, cmdr)


def prefs_changed(cmdr: str, is_beta: bool) -> None:
    """
    Save settings.
    """
    this.Ui.save_prefs(cmdr)


def journal_entry(cmdr, is_beta, system, station, entry, state):
    """
    Parse an incoming journal entry and store the data we need
    """
    this.journal_entry(cmdr, is_beta, system, station, entry, state)
