# core/views/__init__.py

# Importa todas as views dos módulos separados para o namespace 'views'.
# Isso permite que o urls.py continue a usar 'views.NomeDaView' sem alterações.

from .dashboard_views import *
from .auth_views import *
from .conta_views import *
from .cartao_views import *
from .categoria_views import *
from .lancamento_views import *
from .import_views import *
from .regra_views import *