class Plugin:
    def __init__(self, app_state, config):
        """
        app_state: MdViewerState instance or None if not applicable
        config: Application configuration dictionary
        """
        self.state = app_state
        self.config = config

    def register_routes(self, app):
        """
        Register routes onto the Flask/Werkzeug app instance.
        app is the main App class instance.
        You can add endpoints to app.url_map using app.url_map.add(Rule(...))
        and attach handlers to app instance, e.g., setattr(app, 'on_myroute', self.my_handler)
        Wait, Werkzeug map can be updated dynamically, or we return rules and handlers.
        """
        pass
