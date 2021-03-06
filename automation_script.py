import os
import shutil
import csv

from re import sub, split, findall
from base64 import urlsafe_b64decode
from random import randint

from googleapiclient.discovery import Resource

from gmail_actions import obtener_servicio
from gmail_actions import listar_mensajes_por_fechas, obtener_adjuntos
from gmail_actions import crear_mensaje, enviar_mensaje

from datetime import datetime
from zipfile import ZipFile, BadZipFile
from py7zr import SevenZipFile, Bad7zFile
from unrar.rarfile import RarFile, BadRarFile
from io import BytesIO


FORMATO_FECHA_VALIDO = '%d/%m/%Y %H:%M:%S'

ARCHIVO_ALUMNOS = 'Listado Algo I - 202102 - Regulares.csv'

EXTENSIONES_DE_COMPRESION = ['.zip', '.rar', '.7z']


def leer_archivo(ruta_de_archivo: str) -> 'list[str]':

    # PRE: 'ruta_de_archivo', debe ser una variable de tipo str
    # POST: Devuelve una lista, que representa a las lineas leidas del archivo  
    #       que fue abierto y leido posteriormente

    datos = []
    archivo = open(ruta_de_archivo, 'r', encoding='utf-8')

    try:
        with archivo:
            datos = archivo.read().splitlines()

    except IOError:
        print('\nNo se pudo leer el archivo: ', ruta_de_archivo)
    
    finally:
        archivo.close()

    return datos


def escribir_archivo(ruta_de_archivo: str, contenido: str) -> None:

    archivo = open(ruta_de_archivo, 'w', encoding='utf-8')

    try:
        with archivo:
            archivo.write(contenido)      

    except IOError:
        print('\nNo se pudo escribir el archivo: ', ruta_de_archivo)

    finally:
        archivo.close()      


def escribir_archivo_binario(ruta_de_archivo: str, contenido: str) -> None:

    archivo_bytes = BytesIO(contenido)

    objetivo = open(ruta_de_archivo, 'wb') 

    try:
        with archivo_bytes, objetivo:

            shutil.copyfileobj(archivo_bytes, objetivo)      

    except IOError:
        print('\nNo se pudo escribir el archivo: ', ruta_de_archivo)

    finally:
        objetivo.close()         


def eliminar_archivos_temporales(nombre_de_directorio: str) -> None:

    for archivos in os.listdir(nombre_de_directorio):

        ruta_de_archivo = os.path.join(nombre_de_directorio, archivos)

        try:
            shutil.rmtree(ruta_de_archivo)

        except OSError:
            os.remove(ruta_de_archivo)    


def obtener_lista_de_archivos(nombre_de_directorio: str) -> 'list[str]':

    archivos = os.listdir(nombre_de_directorio)
    todos_los_archivos = list()

    for entrada in archivos:

        ruta_completa = os.path.join(nombre_de_directorio, entrada)

        if os.path.isdir(ruta_completa):

            todos_los_archivos = todos_los_archivos + obtener_lista_de_archivos(ruta_completa)
        else:

            todos_los_archivos.append(ruta_completa)
                
    return todos_los_archivos


def obtener_encabezado(mensaje: dict, encabezado: str) -> str:
    '''
    Encabezados v??lidos: 
        'Delivered-To', 'Received', 'X-Received', 'ARC-Seal', 'ARC-Message-Signature', 
        'ARC-Authentication-Results', 'Return-Parh', 'Received', 'Received-SPF', 
        'Authentication-Results', 'DKIM-Signature', 'X-Google-DKIM-Signature', 
        'X-Gm-Message-State', 'X-Google-Smtp-Source', 'X-Received', 'MIME-Version', 
        'From', 'Date', 'Message-ID', 'Subject', 'To', 'Content-Type'
    '''
    asunto = ''
    encabezados = mensaje.get('payload', '').get('headers', '')

    encabezado = [d for d in encabezados if d.get('name', '') == encabezado]

    if encabezado:

        asunto = encabezado[0].get('value', '')     

    return asunto


# ---------------------------------------------------------------- #
# -------------- INICIO: INTERACCIONES/VALIDACIONES -------------- #
# ---------------------------------------------------------------- #

def validar_formato_archivo(nombre_de_archivo: str) -> 'list[str]':

    errores = list()

    partes = nombre_de_archivo.split('-')

    if len(partes) == 3:
        
        legajo = validar_numero(partes[0])

        if legajo == 0:

            errores.append('\n\t\tEl n??mero de padr??n/documento debe consistir solo en n??meros')

    else:

        errores.append('\n\t\tNo se encontr?? formato {0} ?? {1}'
            .format(
                '\'[N_Padron] - [Apellido], [Nombre] - E[N_Ejercicio]\'',
                '\'[N_Padron] - [Apellido], [Nombre] - DNI[F/D]\''
            )
        )

    return errores


def validar_archivo_en_zip(nombre_de_archivo: str) -> 'list[str]':

    errores = list()

    extension = findall("\.[0-9a-z]+$", nombre_de_archivo)

    if extension:

        nombre_de_archivo = nombre_de_archivo.replace(extension[0], '')
        errores += validar_formato_archivo(nombre_de_archivo)

    else:

        errores.append('\n\t\tNo hay extensi??n de archivo o es carpeta')
        errores += validar_formato_archivo(nombre_de_archivo)

    return errores


def validar_archivos_en_7z(archivo: str) -> 'list[str]':

    informe_general = list()
    nombres_de_archivos = list()

    dato = urlsafe_b64decode(archivo.encode('KOI8-U'))

    archivo_bytes = BytesIO(dato)

    with SevenZipFile(archivo_bytes) as archivo_7z:

        archivo_7z.extractall(path='tmp\\')

        nombres_de_archivos = obtener_lista_de_archivos('tmp\\')

        if nombres_de_archivos:

            for nombre_de_archivo in nombres_de_archivos:

                resumen = ''
                errores = list()

                nombre_normalizado =  normalizar_nombre_de_archivo(nombre_de_archivo)

                errores = validar_archivo_en_zip(nombre_normalizado)

                resumen = ''.join(errores)

                if resumen:

                    resumen = f'Archivo "{nombre_normalizado}": {resumen}\n'

                    informe_general.append(resumen)    

        else:

            resumen = f'No hay archivos adjuntos o es una carpeta vac??a\n'

            informe_general.append(resumen)

    eliminar_archivos_temporales('tmp\\')

    return informe_general


def validar_archivos_en_rar(archivo: str, nombre_de_comprimido: str) -> 'list[str]':
    
    informe_general = list()
    nombres_de_archivos = list()

    dato = urlsafe_b64decode(archivo.encode('KOI8-U'))

    escribir_archivo_binario(f'tmp\\{nombre_de_comprimido}', dato)

    with RarFile(f"tmp\\{nombre_de_comprimido}") as archivo_rar:

        archivo_rar.extractall(path='tmp\\')

        os.remove(f"tmp\\{nombre_de_comprimido}")

        nombres_de_archivos = obtener_lista_de_archivos('tmp\\')

        if nombres_de_archivos:

            for nombre_de_archivo in nombres_de_archivos:

                resumen = ''
                errores = list()

                nombre_normalizado =  normalizar_nombre_de_archivo(nombre_de_archivo)

                errores = validar_archivo_en_zip(nombre_normalizado)

                resumen = ''.join(errores)

                if resumen:

                    resumen = f'Archivo "{nombre_normalizado}": {resumen}\n'

                    informe_general.append(resumen)    

        else:

            resumen = f'No hay archivos adjuntos o es una carpeta vac??a\n'

            informe_general.append(resumen)

    eliminar_archivos_temporales('tmp\\')

    return informe_general


def validar_archivos_en_zip(archivo: str) -> 'list[str]':

    informe_general = list()

    dato = urlsafe_b64decode(archivo.encode('KOI8-U'))

    archivo_bytes = BytesIO(dato)

    with ZipFile(archivo_bytes) as archivo_zip:

        nombres_de_archivos = archivo_zip.namelist()

        for nombre_de_archivo in nombres_de_archivos:

            nombre_normalizado =  normalizar_nombre_de_archivo(nombre_de_archivo)

            if nombre_normalizado:

                resumen = ''
                errores = list()

                errores = validar_archivo_en_zip(nombre_normalizado)

                resumen = ''.join(errores)

                if resumen:

                    resumen = f'Archivo "{nombre_normalizado}": {resumen}\n'

                    informe_general.append(resumen)

    return informe_general


def es_opcion_valida(opcion: str, opciones: list) -> bool:

    # PRE: 'opcion', debe ser una variable de tipo str
    #      'opciones', debe ser una variable de tipo list
    # POST: Devuelve un boolean, que representa a si la opcion pasada 
    #       por par??metro, es un n??mero y si se encuentra dentro del 
    #       rango de las posibles opciones a elegir

    numero_opcion = 0
    flag_opcion_valida = False

    if opcion.isnumeric():
        numero_opcion = int(opcion)

        if numero_opcion > 0 and numero_opcion <= len(opciones):
            flag_opcion_valida = True

        else:
            print(f'\n??S??lo puedes ingresar una opci??n entre el 1 y el {len(opciones)}!')

    else:
        print(f'\n??Las opciones son numeros enteros, sin decimales!')

    return flag_opcion_valida


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

            print(f'\n??Formato de fecha incorrecto, debe ser del tipo {FORMATO_FECHA_VALIDO}!')
            print('Ejemplo: 12/06/2021 17:00:00\n')

            fecha = input('Ingrese una fecha: ')

    return fecha, fecha_validada


def validar_numero(numero: str) -> int:

    # PRE: 'numero', debe ser una variable de tipo str
    # POST: Devuelve un int o float, que representa al n??mero pasado por 
    #       par??metro, al cual se le ha eliminado los caracteres alfabeticos

    numero_formateado = ''
    valor = 0

    numero_formateado = sub('[a-zA-Z]+', '', numero)

    try:
        valor = int(numero_formateado)

    except ValueError:

        print('\n??S??lo se pueden ingresar numeros!')

    return valor


def validar_opcion_ingresada(opciones: list) -> int:

    # POST: Devuelve un int, que representa a la entrada hecha por el  
    #       usuario, de una opcion, a la cual se la valida  

    opcion_ingresada = ''
    numero = 0
    flag_opcion_valida = False

    opcion_ingresada = input('\nIngrese una opci??n: ')

    while not flag_opcion_valida:

        numero = validar_numero(opcion_ingresada)
        flag_opcion_valida = es_opcion_valida(opcion_ingresada, opciones)

        if not flag_opcion_valida:

            opcion_ingresada = input('\nIngrese una opci??n: ')

    return numero


def obtener_fecha() -> tuple:

    fecha = ''
    fecha_validada = None

    print('El formato de fecha v??lido, debe ser del tipo \'12/06/2021 17:00:00\'\n')

    fecha, fecha_validada = validar_formato_fecha()

    return fecha, fecha_validada


def obtener_fechas() -> tuple:

    fecha_inicio = ''
    fecha_hasta = ''
    fecha_inicio_validada = None
    fecha_hasta_validada = None
    flag_fechas_validas = False

    while not flag_fechas_validas:

        print('\nSe deber?? ingresar una fecha inicio')
        fecha_inicio, fecha_inicio_validada = obtener_fecha()

        print('\nSe deber?? ingresar una fecha hasta')
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

    print('\nOpciones v??lidas: \n')

    for x in range(len(opciones)):
        print(x + 1, '-', opciones[x])

    opcion = validar_opcion_ingresada(opciones)

    return opcion


# ---------------------------------------------------------------- #
# --------------- FIN : INTERACCIONES/VALIDACIONES --------------- #
# ---------------------------------------------------------------- #


def asignar_correctores_a_alumnos() -> 'list[dict]':

    datos = [
        'Ariadna Cattaneo', 'Bruno Lanzillota', 
        'Carolina Di Matteo', 'Daniela Palacios', 'Franco Capra',
        'Franco Lucchesi', 'Guido Costa', "Lautaro D'Abbraccio", 
        'Leonel Chaves', 'Mart??n Sosa', 'Ramiro Esperon',
        'Tomas Villegas'
    ]

    texto = ''
    correctores = list()
    correctores_asignados = list()
    flag_estan_todos_asignados = False
    resultados = leer_archivo('informe_alumnos.csv')

    victimas = list(resultados[1:])
    victimas = [i for i in victimas if i]

    cant_victimas_por_corrector = len(victimas) // len(datos)
    resto_victimas = len(victimas) % len(datos)

    for dato in datos:

        victimas_por_corrector = list()

        for i in range(cant_victimas_por_corrector):

            indice = randint(0, len(victimas) - 1)

            victima = victimas.pop(indice)

            victimas_por_corrector.append(victima)

        corrector = {
            'corrector': dato,
            'estudiantes': list(victimas_por_corrector)
        }

        correctores.append(corrector)

    victimas_remanentes = list(victimas)

    while victimas_remanentes:

        indice_corrector = randint(0, len(datos) - 1)

        while indice_corrector in correctores_asignados:

            indice_corrector = randint(0, len(datos) - 1)

        indice = randint(0, len(victimas_remanentes) - 1)

        victima = victimas_remanentes.pop(indice)

        correctores[indice_corrector].get('estudiantes', []).append(victima)

        correctores_asignados.append(indice_corrector)

    for corrector in correctores:
        
        legajos = list()

        for victima in corrector.get('estudiantes', []):

            legajo = 0

            texto += f"{victima},{corrector.get('corrector', '')}\n"

            legajo = int(victima.split(',')[0])

            legajos.append(legajo)
        
        corrector['legajos'] = legajos
        corrector.pop('estudiantes')

    escribir_archivo('alumnos_por_corrector.txt', texto)

    return correctores


def generar_informe_de_entregas(estudiantes: 'list[dict]') -> None:

    informe = ''

    columnas = ['legajo', 'apellido', 'nombre', 'entregaFormatoValido']

    informe += f"{','.join(columnas)}\n"

    for estudiante in estudiantes:

        texto = [str(estudiante.get(llave, '')) for llave in columnas]

        informe += f"{','.join(texto)}\n"

    escribir_archivo('informe_alumnos.csv', informe)

    
def normalizar_nombre_de_archivo(nombre_de_archivo: str) -> str:

    nombre_normalizado = ''

    extension = findall("\.[0-9a-z]+$", nombre_de_archivo)

    if extension:

        partes = split(r'/|\\', nombre_de_archivo)

        nombre_normalizado = partes[len(partes) - 1]

    return nombre_normalizado


def desempaquetar_archivo_7z(carpeta: str, archivo: str) -> None:

    dato = urlsafe_b64decode(archivo.encode('KOI8-U'))

    archivo_bytes = BytesIO(dato)

    with SevenZipFile(archivo_bytes) as archivo_7z:

        archivo_7z.extractall(path='tmp\\')

        nombres_de_archivos = obtener_lista_de_archivos('tmp\\')

        for nombre_de_archivo in nombres_de_archivos:

            nombre_normalizado =  normalizar_nombre_de_archivo(nombre_de_archivo)

            shutil.move(nombre_de_archivo, f'{carpeta}\\{nombre_normalizado}')

    eliminar_archivos_temporales('tmp\\')


def desempaquetar_archivo_rar(carpeta: str, nombre_de_comprimido: str, archivo: str):

    dato = urlsafe_b64decode(archivo.encode('KOI8-U'))

    escribir_archivo_binario(f'tmp\\{nombre_de_comprimido}', dato)

    with RarFile(f"tmp\\{nombre_de_comprimido}") as archivo_rar:

        archivo_rar.extractall(path='tmp\\')

        os.remove(f"tmp\\{nombre_de_comprimido}")

        nombres_de_archivos = obtener_lista_de_archivos('tmp\\')

        for nombre_de_archivo in nombres_de_archivos:

            nombre_normalizado =  normalizar_nombre_de_archivo(nombre_de_archivo)

            shutil.move(nombre_de_archivo, f'{carpeta}\\{nombre_normalizado}')

    eliminar_archivos_temporales('tmp\\')


def desempaquetar_archivo_zip(carpeta: str, archivo: str) -> None:

    dato = urlsafe_b64decode(archivo.encode('KOI8-U'))

    archivo_bytes = BytesIO(dato)

    with ZipFile(archivo_bytes) as archivo_zip:

        for elemento in archivo_zip.namelist():
            
            nombre_normalizado =  normalizar_nombre_de_archivo(elemento)

            if nombre_normalizado:

                fuente = archivo_zip.open(elemento)
                objetivo = open(f'{carpeta}\\{nombre_normalizado}', 'wb')

                try:
                    with fuente, objetivo:

                        shutil.copyfileobj(fuente, objetivo)       

                except IOError:
                    print('\nNo se pudo escribir el archivo: ', elemento)

                finally:
                    objetivo.close()                        


def guardar_comprimido(extension: str, carpeta: str, nombre_de_comprimido: str, dato: str) -> None:

    if extension in EXTENSIONES_DE_COMPRESION:

        try:

            if extension == '.zip':

                desempaquetar_archivo_zip(carpeta, dato)

            elif extension == '.rar':
                
                desempaquetar_archivo_rar(carpeta, nombre_de_comprimido, dato)

            elif extension == '.7z':
                
                desempaquetar_archivo_7z(carpeta, dato)
            
        except (BadZipFile, BadRarFile, Bad7zFile):
            
            archivo = urlsafe_b64decode(dato.encode('KOI8-U'))

            archivo_bytes = BytesIO(archivo)      

            objetivo = open(f'{carpeta}\\{nombre_de_comprimido}', 'wb') 

            with archivo_bytes, objetivo:

                shutil.copyfileobj(archivo_bytes, objetivo)                    


def guardar_archivos(correctores: 'list[dict]', estudiantes: 'list[dict]') -> None:
    

    for corrector in correctores:

        os.makedirs(corrector.get('corrector'), exist_ok=True)

        estudiantes_por_corrector = list()

        estudiantes_por_corrector = [i for i in estudiantes if i.get('legajo', 0) in corrector.get('legajos', [])]        

        for estudiante in estudiantes_por_corrector: 

            nombre_completo = "{0}\\{1} {2}".format(
                corrector.get('corrector'),
                estudiante.get('apellido', ''),
                estudiante.get('nombre', '')
            )

            os.makedirs(nombre_completo, exist_ok=True)

            for archivo in estudiante.get('archivos', []):

                guardar_comprimido(
                    archivo.get('extension', ''),
                    nombre_completo,
                    archivo.get('filename', ''),
                    archivo.get('data', '')
                )


def buscar_indice_estudiante(estudiantes: 'list[dict]', legajo: int) -> int:

    indice = 0
    flag_se_encontro_indice = False

    while not flag_se_encontro_indice and indice < len(estudiantes):

        if estudiantes[indice].get('legajo', 0) == legajo:

            flag_se_encontro_indice = True

        else:

            indice += 1

    if indice == len(estudiantes):

        indice = -1

    return indice


def actualizar_entregas_e_informes(servicio: Resource, fecha_inicio: str, 
                                   fecha_hasta: str, estudiantes: 'list[dict]') -> None: 

    mensajes_actualizados = listar_mensajes_por_fechas(servicio, fecha_inicio, fecha_hasta)

    estudiantes_actualizados = procesar_informacion_de_entrada()

    limpiar_estudiantes(mensajes_actualizados, estudiantes_actualizados)
    limpiar_mensajes(mensajes_actualizados)
    unir_mensajes_a_estudiantes(estudiantes_actualizados, mensajes_actualizados)

    for estudiante in estudiantes:

        # Eliminamos los estudiantes que ya entregaron y est?? OK
        if estudiante.get('entregaFormatoValido', False):

            indice = buscar_indice_estudiante(estudiantes_actualizados, estudiante.get('legajo', 0))

            if indice != -1:

                del estudiantes_actualizados[indice]

    obtener_adjuntos_por_estudiante(servicio, estudiantes_actualizados)

    for estudiante in estudiantes:

        # De aquellos estudiantes con los que contamos con entrega pero no est??n OK
        # le asignamos los nuevos archivos descargados y eliminamos al mismo de la lista
        # actualizada
        if not estudiante.get('entregaFormatoValido', False):

            indice = buscar_indice_estudiante(estudiantes_actualizados, estudiante.get('legajo', 0))

            if indice != -1:

                estudiante['archivos'] = estudiantes_actualizados[indice].get('archivos', '')
                estudiante['mensajeEnviado'] = False

                del estudiantes_actualizados[indice]

    estudiantes += estudiantes_actualizados

    generar_informe_de_entregas_validas(servicio, estudiantes)


def generar_informe_de_entregas_validas(servicio: Resource, estudiantes: 'list[dict]') -> None:

    informe_general_entregas_invalidas = ''
    informe_general_entregas_validas = ''

    for estudiante in estudiantes:

        informe_individual = list()

        if estudiante.get('archivos', [])[0].get('extension') == '.zip':

            try:

                informe_individual = validar_archivos_en_zip(
                    estudiante.get('archivos', '')[0].get('data', '')
                )

            except BadZipFile:

                informe_individual.append('Archivo "{0}": {1}\n'
                    .format(
                        estudiante.get('archivos', '')[0].get('filename', ''),
                        '\n\t\tSe cambi?? la extensi??n, no es un .zip'
                    )
                )

        elif estudiante.get('archivos', '')[0].get('extension') == '.rar':

            try:

                informe_individual = validar_archivos_en_rar(
                    estudiante.get('archivos', '')[0].get('data', ''),
                    estudiante.get('archivos', '')[0].get('filename', '')
                )

            except BadRarFile:

                informe_individual.append('Archivo "{0}": {1}\n'
                    .format(
                        estudiante.get('archivos', '')[0].get('filename', ''),
                        '\n\t\tSe cambi?? la extensi??n, no es un .rar'
                    )
                )                                

        elif estudiante.get('archivos', '')[0].get('extension') == '.7z':

            try:

                informe_individual = validar_archivos_en_7z(
                    estudiante.get('archivos', '')[0].get('data', '')
                )

            except Bad7zFile:

                informe_individual.append('Archivo "{0}": {1}\n'
                    .format(
                        estudiante.get('archivos', '')[0].get('filename', ''),
                        '\n\t\tSe cambi?? la extensi??n, no es un .7z'
                    )
                )  

        else:

            informe_individual.append('Archivo "{0}": {1} {2}\n'
                .format(
                    estudiante.get('archivos', '')[0].get('filename', ''),
                    '\n\t\tNo es un archivo comprimido',
                    estudiante.get('archivos', '')[0].get('extension', '')
                )
            )

        if not informe_individual:

            estudiante['entregaFormatoValido'] = True

            informe_individual_entrega_valida = '{0} - {1} {2}: ENTREGA OK\n'.format(
                estudiante.get('legajo', 0),
                estudiante.get('apellido', ''),
                estudiante.get('nombre', '')               
            )

            informe_general_entregas_validas += informe_individual_entrega_valida

            if not estudiante.get('mensajeEnviado', False):

                mensaje = crear_mensaje(
                    obtener_encabezado(estudiante.get('mensaje', ''), 'To'),
                    obtener_encabezado(estudiante.get('mensaje', ''), 'From'),
                    obtener_encabezado(estudiante.get('mensaje', ''), 'Subject'),
                    informe_individual_entrega_valida,
                    obtener_encabezado(estudiante.get('mensaje', ''), 'Message-ID'),
                    estudiante.get('mensaje', dict()).get('threadId', '')
                )

                enviar_mensaje(servicio, mensaje)

                estudiante['mensajeEnviado'] = True

        else:
            
            informe_individual_entrega_invalida = "{0} - {1} {2}: \n".format(
                estudiante.get('legajo', 0),
                estudiante.get('apellido', ''),
                estudiante.get('nombre', '')
            )

            for error in informe_individual:

                informe_individual_entrega_invalida += f'\t{error}\n'

            informe_general_entregas_invalidas += informe_individual_entrega_invalida
            informe_general_entregas_invalidas += '\n'

            if not estudiante.get('mensajeEnviado', False):

                mensaje = crear_mensaje(
                    obtener_encabezado(estudiante.get('mensaje', ''), 'To'),
                    obtener_encabezado(estudiante.get('mensaje', ''), 'From'),
                    obtener_encabezado(estudiante.get('mensaje', ''), 'Subject'),
                    informe_individual_entrega_invalida,
                    obtener_encabezado(estudiante.get('mensaje', ''), 'Message-ID'),
                    estudiante.get('mensaje', dict()).get('threadId', '')
                )

                enviar_mensaje(servicio, mensaje)

                estudiante['mensajeEnviado'] = True            

    escribir_archivo('entregas_invalidas.txt', informe_general_entregas_invalidas)
    escribir_archivo('entregas_validas.txt', informe_general_entregas_validas)


def obtener_adjuntos_por_estudiante(servicio: Resource, estudiantes: 'list[dict]') -> None:

    archivos = list()

    for estudiante in estudiantes:

        archivos = obtener_adjuntos(servicio, estudiante.get('mensaje', dict()))

        estudiante['archivos'] = archivos


def unir_mensajes_a_estudiantes(estudiantes: 'list[dict]', mensajes: 'list[dict]'):

    for estudiante in estudiantes:

        indice = 0
        flag_se_agrego_mensaje = False

        while not flag_se_agrego_mensaje and indice < len(mensajes):

            if estudiante.get('legajo', 0) == mensajes[indice].get('legajo', 0):

                estudiante['mensaje'] = mensajes[indice]
                
                del mensajes[indice]['legajo']

                flag_se_agrego_mensaje = True

            else:

                indice += 1

        estudiante['entregaFormatoValido'] = False
        estudiante['mensajeEnviado'] = False


def eliminar_mensajes_mas_viejos(mensajes: 'list[dict]', indices: 'list[int]') -> None:

    for i in range(len(indices) - 1, 0, -1):

        mensajes.pop(indices[i])


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


def limpiar_mensajes_sin_adjunto(mensajes: 'list[dict]') -> None:

    for i in range(len(mensajes) - 1, -1, -1):

        partes = mensajes[i].get('payload', '').get('parts', '')[1:]

        for parte in partes:

            id_archivo_adjunto = parte.get('body', '').get('attachmentId', '')

            if not id_archivo_adjunto:

                del mensajes[i]


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

    limpiar_mensajes_sin_adjunto(mensajes)


def limpiar_estudiantes(mensajes: 'list[dict]', estudiantes: 'list[dict]') -> None:

    asunto = ''
    legajo = 0
    legajos = list()

    for mensaje in mensajes:

        asunto = obtener_encabezado(mensaje, 'Subject')

        asunto = sub('(\D+\d?\D)', '', asunto)

        legajo = validar_numero(asunto)

        legajos.append(legajo)

        mensaje['legajo'] = legajo

    legajos = list(filter(lambda i: i != 0, legajos))

    legajos_unicos = set(legajos)

    estudiantes[:] = [i for i in estudiantes if i.get('legajo', 0) in legajos_unicos]


def convertir_dato_a_estudiante(dato: str, encabezados_de_estudiante: 'list[str]') -> dict:
    
    # PRE: 'dato', debe ser una variable de tipo str
    #      'encabezados_de_estudiante', debe ser una lista de str
    # POST: Devuelve un dict, que representa a la informaci??n pasada por 
    #       par??metro y que ha sido parseada al modelo 'estudiante'

    # estudiante = { 
    #   'legajo': int, 
    #   'nombre': str, 
    #   "apellido": str
    # }

    dato_formateado = list()
    estudiante = dict()

    dato_formateado = split('\,\"|\,\s*|\"\,|\,', dato)
    dato_formateado = dato_formateado[1:4]

    for x in range(len(encabezados_de_estudiante)):

        if encabezados_de_estudiante[x] == 'legajo':
            estudiante[encabezados_de_estudiante[x]] = validar_numero(dato_formateado[x])

        else:
            estudiante[encabezados_de_estudiante[x]] = dato_formateado[x]        

    return estudiante


def normalizar_datos_de_estudiantes(datos_no_normalizados: 'list[str]') -> tuple:

    # Regex para separar por coma y espacio y/o coma '\,\s*|\,'

    encabezados_de_estudiante = list()
    datos_de_estudiantes = list()

    encabezados_de_estudiante = datos_no_normalizados[1:2]
    encabezados_de_estudiante = split('\,\s*|\,', encabezados_de_estudiante[0])

    datos_de_estudiantes = datos_no_normalizados[2:]
    datos_de_estudiantes.pop(-1)
    datos_de_estudiantes = [i.title() for i in datos_de_estudiantes]

    encabezados_de_estudiante = encabezados_de_estudiante[1:2]
    encabezados_de_estudiante = [i.lower() for i in encabezados_de_estudiante]
    encabezados_de_estudiante.append('apellido')
    encabezados_de_estudiante.append('nombre')

    return encabezados_de_estudiante, datos_de_estudiantes


def procesar_informacion_de_entrada() -> 'list[dict]':

    # POST: Devuelve una lista de dicts, que representa a la 
    #       informaci??n procesada del archivo 'ARCHIVO_ALUMNOS'  

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


def obtener_correctores() -> 'list[dict]':
    file = open('asignacion_de_correctores.csv', encoding='utf-8')

    csv_reader = csv.reader(file)

    datos_no_normalizados = list(csv_reader)

    datos_no_normalizados.pop(0)

    correctores = [x[3] for x in datos_no_normalizados]

    correctores_unicos = set(correctores)

    correctores = list()

    for nombre in correctores_unicos:

        corrector = dict()

        corrector['corrector'] = nombre

        estudiantes = [x[0] for x in datos_no_normalizados if x[3] == nombre]

        corrector['estudiantes'] = [int(x) for x in estudiantes]

        correctores.append(corrector)    

    return correctores


#TODO: Eliminar mensajes sin attachementId, o sea, que no enviaron archivo adjunto
def main() -> None:

    opciones = [
        "Procesar entregas y archivo de alumnos",
        "Generar informe de entregas v??lidas/inv??lidas",
        "Generar informe de entregas",
        "Asignar correctores a alumnos",
        "Guardar archivos",
        "Opci??n 6",
        "Salir"
    ]

    opcion = 0
    fecha_inicio = ''
    fecha_hasta = ''
    mensajes = list()
    estudiantes = list()
    correctores = list()
    flag_hay_datos = False
    flag_primera_descarga = False

    servicio = obtener_servicio()

    os.makedirs('tmp', exist_ok=True)

    opcion = obtener_entrada_usuario(opciones)

    while opcion != 7:

        if opcion == 1:

            # fecha_inicio, fecha_hasta = obtener_fechas()

            mensajes = listar_mensajes_por_fechas(servicio, '02/12/2021 20:30:00', '02/12/2021 21:00:00')
            # mensajes = listar_mensajes_por_fechas(servicio, fecha_inicio, fecha_hasta)

            estudiantes = procesar_informacion_de_entrada()
            
            limpiar_estudiantes(mensajes, estudiantes)
            limpiar_mensajes(mensajes)
            unir_mensajes_a_estudiantes(estudiantes, mensajes)

            print("\n??Entregas y alumnos procesados!")

            flag_hay_datos = True

        elif (opcion == 2 and flag_hay_datos):

            if not flag_primera_descarga:

                obtener_adjuntos_por_estudiante(servicio, estudiantes)
                generar_informe_de_entregas_validas(servicio, estudiantes)

                flag_primera_descarga = True

            else:

                fecha_inicio, fecha_hasta = obtener_fechas()

                actualizar_entregas_e_informes(servicio, fecha_inicio, fecha_hasta, estudiantes)

            print("\n??Informes de entregas v??lidas generados!")

        elif (opcion == 3 and flag_hay_datos):
            
            generar_informe_de_entregas(estudiantes)

            print("\n??Informe de entregas generado!")

        elif (opcion == 4 and flag_hay_datos):
            
            correctores = asignar_correctores_a_alumnos()
            #correctores = obtener_correctores()

            print("\n??Correctores asignados!")

        elif (opcion == 5 and flag_hay_datos):

            guardar_archivos(correctores, estudiantes)

            print("\n??Archivos guardados!")

        elif (opcion == 6):

            pass

        else:

            print("\n??Debes procesar informaci??n primero, antes de elegir esa opci??n!")

        opcion = obtener_entrada_usuario(opciones)

    os.rmdir('tmp\\')

    print("\nPrograma finalizado")


if __name__ == '__main__':
    main()