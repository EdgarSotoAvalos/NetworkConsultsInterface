import sys
from PyQt6 import uic, QtWidgets, QtCore
import socket
import time

#Importamos paramiko para el SSH
import paramiko


#Importamo el diseño ui
qtCreatorFile = "red.ui"
Ui_MainWindow, QtBaseClass = uic.loadUiType(qtCreatorFile) 


# Información de los dispositivos
devices = {
    'iosv-1': {'ip': '192.168.0.1'},
    'iosv-2': {'ip': '192.168.1.1'},
    'iosv-3': {'ip': '192.168.1.6'},
    'iosv-4': {'ip': '192.168.1.14'},
    'rf': {'ip': '192.168.1.22'}
}


# Diccionario de comandos disponibles
commands = {
    'Ver NAT': 'show ip nat translations\n',
    'Ver DHCP': 'show ip dhcp pool\n',
    'Ver Alta disponibilidad': 'show standby brief\n',
    'Ver VLAN en Router': 'show interfaces fastEthernet 1/0\n',
    'Ver Configuración de Interface': 'show running-config interface\n',
    'Ver Interfaces en Router': 'show ip interface brief\n',
    'Ver ACL': 'show access-lists\n',
    'Ver QoS': 'show policy-map interface f0/0\n',
    'Balanceo y Carga': 'show ip ospf interface\n',
    'Protocolo de Enrutamiento': 'show ip protocols\n'
}


# Max buffer
max_buffer = 65535


class MyApp(QtWidgets.QMainWindow, Ui_MainWindow): 

    def __init__(self):
        QtWidgets.QMainWindow.__init__(self) 
        Ui_MainWindow.__init__(self) 
        self.setupUi(self) 

        # Acceder a los widgets definidos en el archivo .ui
        self.labelImagen = self.findChild(QtWidgets.QLabel, 'labelImagen')
        self.scrollArea = self.findChild(QtWidgets.QScrollArea, 'scrollArea')
        self.labelUsuario = self.findChild(QtWidgets.QLabel, 'labelUsuario')
        self.labelPassword = self.findChild(QtWidgets.QLabel, 'labelPassword')
        self.labelDispositivo = self.findChild(QtWidgets.QLabel, 'labelDispositivo')
        self.labelComando = self.findChild(QtWidgets.QLabel, 'labelComando')
        self.labelResultados = self.findChild(QtWidgets.QLabel, 'labelResultados')
        self.inputUsuario = self.findChild(QtWidgets.QLineEdit, 'inputUsuario')
        self.inputPassword = self.findChild(QtWidgets.QLineEdit, 'inputPassword')
        self.comboBoxDispositivo = self.findChild(QtWidgets.QComboBox, 'comboBoxDispositivo')
        self.comboBoxComando = self.findChild(QtWidgets.QComboBox, 'comboBoxComando')
        self.comboBox_2 = self.findChild(QtWidgets.QComboBox, 'comboBox_2')
        self.buttonEjecutar = self.findChild(QtWidgets.QPushButton, 'buttonEjecutar')
        self.frameStatus = self.findChild(QtWidgets.QFrame, 'frameStatus')

         # Crear layout para el frameStatus
        self.status_layout = QtWidgets.QVBoxLayout(self.frameStatus)

        # Crear y agregar labels de estado para cada dispositivo
        self.status_labels = {}
        for device in devices.keys():
            status_label = QtWidgets.QLabel(f'{device}: Checking...')
            status_label.setStyleSheet("""
                background-color: yellow; 
                font-size: 12pt; 
                border: 2px solid black; 
                border-radius: 10px;
                padding: 5px;
            """)
            self.status_layout.addWidget(status_label)
            self.status_labels[device] = status_label

        # Agregar dispositivos al comboBoxDispositivo
        for device, data in devices.items():
            self.comboBoxDispositivo.addItem(device, data['ip'])

        # Cargar opciones al comboBoxDispositivo
        for command in commands.keys():
            self.comboBoxComando.addItem(command, command)

        # Conectar señales y slots si es necesario y ejecutar el comando
        self.buttonEjecutar.clicked.connect(self.execute_command)

        # Crear un temporizador para actualizar el estado de los dispositivos
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_router_status)
        self.timer.start(5000)  # Actualizar cada 5 segundos

        #Mostramos la ventana
        self.show()

    
    def clear_buffer(self, connection):
        if connection.recv_ready():
            return connection.recv(max_buffer)


    def check_router_status(self, device_ip):
        try:
            socket.setdefaulttimeout(2)
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((device_ip, 22))
            s.close()
            return True
        except Exception as e:
            return False
        

    def update_router_status(self):
        for device, info in devices.items():
            device_ip = info['ip']
            status = self.check_router_status(device_ip)
            if status:
                self.status_labels[device].setStyleSheet("""
                    background-color: green; 
                    font-size: 12pt; 
                    border: 2px solid black; 
                    border-radius: 10px;
                    padding: 5px;
                """)
                self.status_labels[device].setText(f'{device}: Online')
            else:
                self.status_labels[device].setStyleSheet("""
                    background-color: red; 
                    font-size: 12pt; 
                    border: 2px solid black; 
                    border-radius: 10px;
                    padding: 5px;
                """)
                self.status_labels[device].setText(f'{device}: Offline')


    def execute_command(self):
        username = self.inputUsuario.text()
        password = self.inputPassword.text()
        device = self.comboBoxDispositivo.currentText()  # Obtener el nombre del dispositivo seleccionado
        device_ip = self.comboBoxDispositivo.currentData()  # Obtener la IP del dispositivo seleccionado
        comando_nombre = self.comboBoxComando.currentText()  # Obtener el nombre del comando seleccionado
        command = commands.get(comando_nombre, '')  # Obtener los datos del comando seleccionado


        # Verificar si algún campo está vacío
        if not username or not password or not device or not comando_nombre:
            QtWidgets.QMessageBox.warning(self, "Error", "Todos los campos son obligatorios")
            return
        
        
        if not self.check_router_status(device_ip):
            QtWidgets.QMessageBox.warning(self, "Error", f"No se pudo conectar al router {device} ({device_ip})")
            return
        
        try:
            connection = paramiko.SSHClient()
            connection.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            connection.connect(device_ip, username=username, password=password, look_for_keys=False, allow_agent=False)
            new_connection = connection.invoke_shell()
            self.clear_buffer(new_connection)
            time.sleep(2)
            new_connection.send("terminal length 0\n")
            self.clear_buffer(new_connection)
            new_connection.send(command)
            time.sleep(2)
            output = new_connection.recv(max_buffer).decode('utf-8')
            self.labelResultados.setText(output)
            new_connection.close()
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Error", f"No se pudo ejecutar el comando: {e}")


        #texto = f"Usuario: {username}\nPassword: {password}\nDispositivo:{device_ip}\nComando: {command}"

        # Actualizar el QLabel con los resultados
        #self.labelResultados.setText(texto)

if __name__ == "__main__": 

    app = QtWidgets.QApplication(sys.argv) 
    window = MyApp() 
    app.exec()

