from waitress import serve
import app_hw2

serve(app_hw2.server, port=80)
