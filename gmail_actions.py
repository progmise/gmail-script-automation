import os

from googleapiclient.discovery import Resource, build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from datetime import datetime
from time import mktime
from re import findall

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# Archivo generado para la API
ARCHIVO_SECRET_CLIENT = 'credentials.json'

FORMATO_FECHA_VALIDO = '%d/%m/%Y %H:%M:%S'


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


def obtener_servicio() -> Resource:
    """
    Creador de la conexion a la API Gmail
    """
    return build('gmail', 'v1', credentials=generar_credenciales())


def obtener_adjunto(servicio: Resource, id_mensaje: str, id_archivo_adjunto: str) -> dict:

    resultado = servicio.users().messages().attachments().get(
        userId='me', 
        messageId=id_mensaje,
        id=id_archivo_adjunto
    ).execute()

    return resultado


def obtener_adjuntos(servicio: Resource, mensaje: dict) -> 'list[dict]':

    resultados = list()
    partes = list()
    archivo_adjunto = dict()

    partes = mensaje.get('payload', '').get('parts', '')[1:]

    for parte in partes:

        id_mensaje = mensaje.get('id', '')
        id_archivo_adjunto = parte.get('body', '').get('attachmentId', '')

        archivo_adjunto = obtener_adjunto(servicio, id_mensaje, id_archivo_adjunto)
        archivo_adjunto['filename'] = parte.get('filename', '')

        extension = findall("\.[0-9a-z]+$", parte.get('filename', ''))

        if extension:
            archivo_adjunto['extension'] = extension[0]

        else:
            archivo_adjunto['extension'] = ''

        resultados.append(archivo_adjunto)

    return resultados


def obtener_mensaje(servicio: Resource, mensaje: dict) -> dict:

    id_mensaje = mensaje.get('id', '')

    resultado = servicio.users().messages().get(userId='me', id=id_mensaje).execute()    

    return resultado


def listar_mensajes_por_fechas(servicio: Resource, fecha_inicio: str, fecha_hasta: str) -> 'list[dict]':

    mensajes = list()

    fecha_minimo = datetime.strptime(fecha_inicio, FORMATO_FECHA_VALIDO)
    fecha_maximo = datetime.strptime(fecha_hasta, FORMATO_FECHA_VALIDO)   

    segundos_fecha_minimo = mktime(fecha_minimo.timetuple())
    segundos_fecha_maximo = mktime(fecha_maximo.timetuple())

    resultados = servicio.users().messages().list(
        userId='me',
        q=f'after:2021/06/15 before:2021/06/16'
    ).execute()

    ids_mensajes = resultados.get('messages', [])

    for id_mensaje in ids_mensajes:

        mensaje = obtener_mensaje(servicio, id_mensaje)
        mensajes.append(mensaje)

    return mensajes