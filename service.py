import os.path
import time
import re
import pytz

from googleapiclient.discovery import Resource, build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from datetime import datetime


SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# Archivo generado para la API
ARCHIVO_SECRET_CLIENT = 'credentials.json'

# Permisos de acceso
PERMISOS = ['https://www.googleapis.com/auth/gmail']

# Zona horaria
TIME_ZONE = 'America/Argentina/Buenos_Aires'

FORMATO_FECHA_VALIDO = '%d/%m/%Y %H:%M:%S'

ARCHIVO_ALUMNOS = 'Listado Algo I - 202101 - Regulares.csv'


def leer_archivo(ruta_de_archivo: str) -> 'list[str]':

    # PRE: 'ruta_de_archivo', debe ser una variable de tipo str
    # POST: Devuelve una lista, que representa a las lineas leidas del archivo  
    #       que fue abierto y leido posteriormente

    datos = []

    try:
        archivo = open(ruta_de_archivo, 'r', encoding='utf-8')
    except IOError:
        print('\nNo se pudo leer el archivo: ', ruta_de_archivo)
    
    with archivo:
        datos = archivo.read().splitlines()

    return datos


def validar_formato_fecha() -> tuple:

    fecha_validada = None
    fecha = ''
    flag_fecha_valida = False

    fecha = input('Ingrese una fecha: ')

    while not flag_fecha_valida:

        try:
            fecha_validada = datetime.strptime(fecha, FORMATO_FECHA_VALIDO)
            flag_fecha_valida= True

        except ValueError:

            print(f'\n¡Formato de fecha incorrecto, debe ser del tipo {FORMATO_FECHA_VALIDO}!')
            print('Ejemplo: 12/06/2021 17:00:00\n')

            fecha = input('Ingrese una fecha: ')

    return fecha, fecha_validada


def validar_numero(numero: str) -> int:

    # PRE: 'numero', debe ser una variable de tipo str
    # POST: Devuelve un int o float, que representa al número pasado por 
    #       parámetro, al cual se le ha eliminado los caracteres alfabeticos

    numero_formateado = ''
    valor = 0

    numero_formateado = re.sub('[a-zA-Z]+', '', numero)

    try:
        valor = int(numero_formateado)

    except ValueError:

        print('\n¡Sólo se pueden ingresar numeros!')

    return valor


def es_opcion_valida(opcion: str, opciones: list) -> bool:

    # PRE: 'opcion', debe ser una variable de tipo str
    #      'opciones', debe ser una variable de tipo list
    # POST: Devuelve un boolean, que representa a si la opcion pasada 
    #       por parámetro, es un número y si se encuentra dentro del 
    #       rango de las posibles opciones a elegir

    numero_opcion = 0
    flag_opcion_valida = False

    if opcion.isnumeric():
        numero_opcion = int(opcion)

        if numero_opcion > 0 and numero_opcion <= len(opciones):
            flag_opcion_valida = True

        else:
            print(f'\n¡Sólo puedes ingresar una opción entre el 1 y el {len(opciones)}!')

    else:
        print(f'\n¡Las opciones son numeros enteros, sin decimales!')

    return flag_opcion_valida


def validar_opcion_ingresada(opciones: list) -> int:

    # POST: Devuelve un int, que representa a la entrada hecha por el  
    #       usuario, de una opcion, a la cual se la valida  

    opcion_ingresada = ''
    numero = 0
    flag_opcion_valida = False

    opcion_ingresada = input('\nIngrese una opción: ')

    while not flag_opcion_valida:

        numero = validar_numero(opcion_ingresada)
        flag_opcion_valida = es_opcion_valida(opcion_ingresada, opciones)

        if not flag_opcion_valida:

            opcion_ingresada = input('\nIngrese una opción: ')

    return numero


def convertir_dato_a_estudiante(dato: str, encabezados_de_estudiante: 'list[str]') -> dict:
    
    # PRE: 'dato', debe ser una variable de tipo str
    # POST: Devuelve un dict, que representa a la información pasada por 
    #       parámetro y que ha sido parseada al modelo 'estudiante'

    # estudiante = { 
    #   'legajo': int, 
    #   'nombre': str, 
    #   "apellido": str
    # }

    dato_formateado = list()
    estudiante = dict()

    dato_formateado = re.split('\,\"|\,\s*|\"\,|\,', dato)
    dato_formateado = dato_formateado[1:4]

    for x in range(len(encabezados_de_estudiante)):

        if encabezados_de_estudiante[x] == 'legajo':
            estudiante[encabezados_de_estudiante[x]] = validar_numero(dato_formateado[x])

        else:
            estudiante[encabezados_de_estudiante[x]] = dato_formateado[x]        

    return estudiante


def normalizar_datos_de_estudiantes(datos_no_normalizados: 'list[str]') -> tuple:

    encabezados_de_estudiante = list()
    datos_de_estudiantes = list()

    encabezados_de_estudiante = datos_no_normalizados[0:1]
    encabezados_de_estudiante = re.split('\,\s*|\,', encabezados_de_estudiante[0])

    datos_de_estudiantes = datos_no_normalizados[2:]
    datos_de_estudiantes = [i.title() for i in datos_de_estudiantes]

    encabezados_de_estudiante = encabezados_de_estudiante[1:2]
    encabezados_de_estudiante = [i.lower() for i in encabezados_de_estudiante]
    encabezados_de_estudiante.append('apellido')
    encabezados_de_estudiante.append('nombre')

    return encabezados_de_estudiante, datos_de_estudiantes


def obtener_fecha() -> tuple:

    fecha = ''
    fecha_validada = None

    print('El formato de fecha válido, debe ser del tipo \'12/06/2021 17:00:00\'\n')

    fecha, fecha_validada = validar_formato_fecha()

    return fecha, fecha_validada


def obtener_fechas() -> tuple:

    fecha_inicio = ''
    fecha_hasta = ''
    fecha_inicio_validada = None
    fecha_hasta_validada = None
    flag_fechas_validas = False

    while not flag_fechas_validas:

        print('\nSe deberá ingresar una fecha inicio')
        fecha_inicio, fecha_inicio_validada = obtener_fecha()

        print('\nSe deberá ingresar una fecha hasta')
        fecha_hasta, fecha_hasta_validada = obtener_fecha()

        if fecha_hasta_validada > fecha_inicio_validada:

            flag_fechas_validas = True

        else:
            print('\nLa segunda fecha debe ser mayor, a la primera fecha')

    return fecha_inicio, fecha_hasta


def obtener_entrada_usuario(opciones: list) -> int:

    # PRE: 'opciones', debe ser una variable de tipo list
    # POST: Devuelve un int, que representa a la entrada hecha por el  
    #       usuario, de una opcion, a la cual se la valida

    opcion = 0

    print('\nOpciones válidas: \n')

    for x in range(len(opciones)):
        print(x + 1, '-', opciones[x])

    opcion = validar_opcion_ingresada(opciones)

    return opcion


def cargar_credenciales() -> Credentials:

    credencial = None

    if os.path.exists('token.json'):
        
        with open('token.json', 'r'):
            credencial = Credentials.from_authorized_user_file('token.json', SCOPES)

    return credencial


def guardar_credenciales(credencial: Credentials) -> None:

    with open('token.json', 'w') as token:
        token.write(credencial.to_json())


def son_credenciales_invalidas(credencial: Credentials) -> bool:

    return not credencial or not credencial.valid


def son_credenciales_expiradas(credencial: Credentials) -> bool:

    return credencial and credencial.expired and credencial.refresh_token


def autorizar_credenciales() -> Credentials:

    flow = InstalledAppFlow.from_client_secrets_file(ARCHIVO_SECRET_CLIENT, SCOPES)

    return flow.run_local_server(open_browser=False, port=0)


def generar_credenciales() -> Credentials:

    credencial = cargar_credenciales()

    if son_credenciales_invalidas(credencial):

        if son_credenciales_expiradas(credencial):
            credencial.refresh(Request())

        else:
            credencial = autorizar_credenciales()

        guardar_credenciales(credencial)

    return credencial


def eliminar_mensajes_mas_viejos(mensajes: 'list[dict]', indices: 'list[int]') -> None:

    for i in range(len(indices) - 1, 0, -1):

        mensajes.pop(indices[i])


def obtener_servicio() -> Resource:
    """
    Creador de la conexion a la API Gmail
    """
    return build('gmail', 'v1', credentials=generar_credenciales())


def obtener_duplicados_por_legajo(mensajes: 'list[dict]') -> dict:

    mensajes_no_unicos_por_legajo = dict()
    index = 0

    for mensaje in mensajes:

        if mensaje['legajo'] in mensajes_no_unicos_por_legajo:

            mensajes_no_unicos_por_legajo[mensaje['legajo']][0] += 1
            mensajes_no_unicos_por_legajo[mensaje['legajo']][1].append(index)

        else:

            mensajes_no_unicos_por_legajo[mensaje['legajo']] = [1, [index]]
        
        index += 1
 
    mensajes_no_unicos_por_legajo = {key:value for key, value in mensajes_no_unicos_por_legajo.items() if value[0] > 1}

    return mensajes_no_unicos_por_legajo


def obtener_encabezado(mensaje: dict, encabezado: str) -> str:
    '''
    Encabezados válidos: 
        'Delivered-To', 'Received', 'X-Received', 'ARC-Seal', 'ARC-Message-Signature', 
        'ARC-Authentication-Results', 'Return-Parh', 'Received', 'Received-SPF', 
        'Authentication-Results', 'DKIM-Signature', 'X-Google-DKIM-Signature', 
        'X-Gm-Message-State', 'X-Google-Smtp-Source', 'X-Received', 'MIME-Version', 
        'From', 'Date', 'Message-ID', 'Subject', 'To', 'Content-Type'
    '''

    encabezados = mensaje.get('payload', '').get('headers', '')

    encabezado = [d for d in encabezados if d.get('name', '') == encabezado]

    asunto = encabezado[0].get('value', '')    

    return asunto


def obtener_mensaje(servicio: Resource, mensaje: dict) -> dict:

    id_mensaje = mensaje.get('id', '')

    resultado = servicio.users().messages().get(userId='me', id=id_mensaje).execute()    

    return resultado


def filtrar_por_fecha_manual(mensajes: 'list[str, dict]', fecha_inicio: str, fecha_hasta: str) -> 'list[dict]':
    '''
    Formato de fecha y hora que se recibe por parámetros:
        12/06/2021 15:40:00  -->  %d/%m/%Y %H:%M:%S

    Formato de fecha y hora que se recibe del servidor: 
        Fri, 11 Jun 2021 20:58:12 -0300  -->  %a, %d %b %Y %H:%M:%S %z
    '''

    zona_horaria = pytz.timezone(TIME_ZONE)
    mensajes_filtrados = list()

    fecha_minimo = datetime.strptime(fecha_inicio, FORMATO_FECHA_VALIDO)
    fecha_maximo = datetime.strptime(fecha_hasta, FORMATO_FECHA_VALIDO)

    fecha_minimo = zona_horaria.localize(fecha_minimo)
    fecha_maximo = zona_horaria.localize(fecha_maximo)    

    for mensaje in mensajes:

        fecha_formateada = datetime.strptime(mensaje.get('fecha', ''), '%a, %d %b %Y %H:%M:%S %z')

        if fecha_minimo < fecha_formateada and fecha_maximo > fecha_formateada:

            mensajes_filtrados.append(mensaje.get('mensaje', ''))

    return mensajes_filtrados


def unir_mensajes_a_estudiantes(estudiantes: 'list[dict]', mensajes: 'list[dict]'):

    for estudiante in estudiantes:

        indice = 0
        flag_se_agrego_mensaje = False

        while not flag_se_agrego_mensaje:

            if estudiante.get('legajo', 0) == mensajes[indice].get('legajo', 0):

                estudiante['mensaje'] = mensajes[indice]
                
                del mensajes[indice]['legajo']

                flag_se_agrego_mensaje = True

            else:

                indice += 1


def limpiar_mensajes(mensajes: 'list[dict]') -> None:

    mensajes_no_unicos_por_legajo = dict()
    flag_no_hay_duplicados = False

    mensajes[:] = list(filter(lambda i: i.get('legajo', 0) != 0, mensajes))

    while not flag_no_hay_duplicados:

        mensajes_no_unicos_por_legajo = obtener_duplicados_por_legajo(mensajes)

        if not bool(mensajes_no_unicos_por_legajo):

            flag_no_hay_duplicados = True

        else:

            eliminar_mensajes_mas_viejos(
                mensajes, 
                list(mensajes_no_unicos_por_legajo.values())[0][1]
            )


def limpiar_estudiantes(mensajes: 'list[dict]', estudiantes: 'list[dict]') -> None:

    asunto = ''
    legajo = 0
    legajos = list()

    for mensaje in mensajes:

        asunto = obtener_encabezado(mensaje, 'Subject')

        asunto = re.sub('(\D+\d?\D)', '', asunto)

        legajo = validar_numero(asunto)

        legajos.append(legajo)

        mensaje['legajo'] = legajo

    legajos = list(filter(lambda i: i != 0, legajos))

    legajos_unicos = set(legajos)

    estudiantes[:] = [i for i in estudiantes if i.get('legajo', 0) in legajos_unicos]


def procesar_informacion_de_entrada() -> 'list[dict]':

    # POST: Devuelve una lista de dicts, que representa a la 
    #       información procesada del archivo 'ARCHIVO_ALUMNOS'  

    encabezados_de_estudiante = list()
    datos_de_estudiantes = list()
    estudiantes = list()

    datos_de_estudiantes = leer_archivo(ARCHIVO_ALUMNOS)

    encabezados_de_estudiante, datos_de_estudiantes = normalizar_datos_de_estudiantes(datos_de_estudiantes)

    for x in range(len(datos_de_estudiantes)):

        estudiantes.append(
            convertir_dato_a_estudiante(datos_de_estudiantes[x], encabezados_de_estudiante)
        )

    return estudiantes


def listar_mensajes_por_fechas(servicio: Resource, fecha_inicio: str, fecha_hasta) -> 'list[dict]':

    mensajes = list()

    fecha_minimo = datetime.strptime(fecha_inicio, FORMATO_FECHA_VALIDO)
    fecha_maximo = datetime.strptime(fecha_hasta, FORMATO_FECHA_VALIDO)   

    segundos_fecha_minimo = time.mktime(fecha_minimo.timetuple())
    segundos_fecha_maximo = time.mktime(fecha_maximo.timetuple())

    resultados = servicio.users().messages().list(
        userId='me', 
        q=f'after:{segundos_fecha_minimo} before:{segundos_fecha_maximo}'
    ).execute()

    ids_mensajes = resultados.get('messages', [])

    for id_mensaje in ids_mensajes:

        mensaje = obtener_mensaje(servicio, id_mensaje)
        '''
        fecha = obtener_encabezado(mensaje, 'Date')
        '''
        mensajes.append(mensaje)
        '''
        mensajes.append({
            'fecha': fecha,
            'mensaje': mensaje
        })
        '''
    '''
    mensajes_filtrados = filtrar_por_fecha_manual(mensajes, fecha_inicio, fecha_hasta)
    '''

    return mensajes


def main() -> None:

    opciones = [
        "Procesar correos electrónicos de entregas y archivo de alumnos",
        "Limpiar alumnos que no realizaron entrega",
        "Descargar códigos fuentes e hipotesis",
        "Opción 4",
        "Opción 5",
        "Salir"
    ]

    opcion = 0
    fecha_inicio = ''
    fecha_hasta = ''
    mensajes = list()
    estudiantes = list()
    flag_hay_datos = False

    servicio = obtener_servicio()
    opcion = obtener_entrada_usuario(opciones)

    while opcion != 6:

        if opcion == 1:

            # fecha_inicio, fecha_hasta = obtener_fechas()

            mensajes = listar_mensajes_por_fechas(servicio, '08/06/2021 18:00:00', '08/06/2021 21:00:00')
            # mensajes = listar_mensajes_por_fechas(servicio, fecha_inicio, fecha_hasta)

            print("\n¡Mensajes procesados!")

            estudiantes = procesar_informacion_de_entrada()

            print("\n¡Estudiantes procesados!")

            flag_hay_datos = True

        elif(opcion == 2 and flag_hay_datos):

            limpiar_estudiantes(mensajes, estudiantes)

            print("\n¡Estudiantes limpiados!")

            limpiar_mensajes(mensajes)

            print("\n¡Mensajes limpiados!")

            unir_mensajes_a_estudiantes(estudiantes, mensajes)

            print("\n¡Se relacionaron estudiantes y mensajes!")

        elif(opcion == 3 and flag_hay_datos):
            pass

        elif(opcion == 4 and flag_hay_datos):
            pass

        elif(opcion == 5 and flag_hay_datos):
            pass

        else:
            print("\n¡Debes procesar información primero, antes de elegir esa opción!")

        opcion = obtener_entrada_usuario(opciones)

    print("\nPrograma finalizado")


if __name__ == '__main__':
    main()