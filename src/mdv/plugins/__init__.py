import importlib
import pkgutil
from mdv.logger import get_logger

logger = get_logger(__name__)

def load_plugins(app, plugins_list):
    """
    Dynamically loads plugins specified in plugins_list ("draw,worklog")
    and registers their routes on the app instance.
    
    In lite mode (single file), only loads plugins relevant to that file type.
    In normal mode (directory), loads all specified plugins.
    """
    if not plugins_list:
        return
    
    plugin_names = [p.strip() for p in plugins_list.split(",") if p.strip()]
    
    # Lite mode detection: single file being viewed
    lite_file = app.config.get("lite_file")
    is_lite_mode = lite_file is not None
    
    # Auto-filter plugins based on file type in lite mode
    if is_lite_mode:
        # csvviewer only useful for CSV files in lite mode
        filtered_names = []
        for name in plugin_names:
            if name == "csvviewer":
                # Only load csvviewer if viewing a CSV file
                if lite_file.endswith('.csv') or app.config.get("csv_mode"):
                    logger.info(f"Auto-loading csvviewer for CSV file: {lite_file}")
                    filtered_names.append(name)
                else:
                    logger.debug(f"Skipping csvviewer (not a CSV file): {lite_file}")
            else:
                filtered_names.append(name)
        plugin_names = filtered_names
    
    for loader, module_name, is_pkg in pkgutil.iter_modules(__path__):
        if module_name in plugin_names:
            logger.info(f"Loading plugin: {module_name}")
            try:
                # Import the module mdv.plugins.<module_name>
                module = importlib.import_module(f".{module_name}", package="mdv.plugins")
                # Ensure it has a setup(app) or Plugin class
                if hasattr(module, "setup_plugin"):
                    module.setup_plugin(app)
                elif hasattr(module, "Plugin"):
                    plugin = module.Plugin(app.state, app.config)
                    plugin.register_routes(app)
                else:
                    logger.warning(f"Plugin {module_name} does not expose 'setup_plugin' or 'Plugin' class.")
            except Exception as e:
                logger.error(f"Failed to load plugin {module_name}: {e}")

