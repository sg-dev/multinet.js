from six.moves import StringIO
import json

from jinja2 import Environment, PackageLoader
template_env = Environment(loader=PackageLoader('multinet', 'templates'))

from IPython.display import HTML, display

def init_3d():
    """Initialise 3D plots within the IPython notebook, by injecting the
    required javascript libraries.
    """

    library_javascript = StringIO()

    library_javascript.write("""
    <p>Loading javascript for 3D plot in browser</p>

    /* Beginning of javascript injected by multinet.js */
    <script type="text/javascript" src="multinet/static/js/jquery-2.1.4.js"></script>
    <script type="text/javascript" src="multinet/static/js/jquery-ui-1.11.4.js"></script>

    <script type="text/javascript" src="multinet/static/js/threejs/three-r71.js"></script>
    <script type="text/javascript" src="multinet/static/js/threejs/orbitcontrols.js"></script>
    <script type="text/javascript" src="multinet/static/js/threejs/stats-r12.min.js"></script>
    <script type="text/javascript" src="multinet/static/js/threejs/detector.js"></script>

    <script type="text/javascript" src="multinet/static/js/multinet-core.js"></script>
    <script type="text/javascript">
        var multinet_javascript_injected = true;
    </script>
    """)

    library_javascript.write(
                "/* End of javascript injected by multinet.js */\n</script>\n")

    display(HTML(library_javascript.getvalue()))


def plot_3d(data):
    template = template_env.get_template('ipnb_multinet.html')
    display(HTML(template.render({'data': json.dumps(data)})))
