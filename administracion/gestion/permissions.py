from rest_framework.permissions import BasePermission

class EsAdmin(BasePermission):
    message= 'No tienes los privilegios suficientes para realizar esta accion'
    def has_permission(self, request, view):
        if not request.user:
            return False
        
        if request.method == 'GET':
            return True
        
        print(request.user.is_anonymous)
        tipoUsuario = request.user.tipoUsuario

        return tipoUsuario == '1'
    
class EsPersonal(BasePermission):
    message= 'No tienes los privilegios suficientes para realizar esta accion'
    def has_permission(self, request, view):

        if request.method == 'GET':
            return True
        
        tipoUsuario = request.user.tipoUsuario

        return tipoUsuario == '3'
    
class EsUsuario(BasePermission):
    message= 'No tienes los privilegios suficientes para realizar esta accion'
    def has_permission(self, request, view):
        
        if request.method == 'GET':
            return True
        
        tipoUsuario = request.user.tipoUsuario

        return tipoUsuario == '2'
    
class EsAdminOrPersonal(BasePermission):
    message= 'No tienes los privilegios suficientes para realizar esta accion'
    def has_permission(self, request, view):
        
        if request.method == 'GET':
            return True
        
        tipoUsuario = request.user.tipoUsuario

        return (tipoUsuario == '1' or tipoUsuario == '2')