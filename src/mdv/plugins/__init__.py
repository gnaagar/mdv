import importlib
import pkgutil
from mdv.logger import get_logger

logger = get_logger(__name__)

def load_plugins(app, plugins_list):
    """
    Dynamically loads plugins specified in plugins_list ("draw,worklog")
    and registers their routes on the app instance.
    """
    if not plugins_list:
        return
        
    plugin_names = [p.strip() for p in plugins_list.split(",") if p.strip()]
    
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

