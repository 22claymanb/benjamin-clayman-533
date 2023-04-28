from waitress import serve
import hw4_app

serve(hw4_app.server, port=80)