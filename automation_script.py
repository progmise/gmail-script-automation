import os
import shutil

from re import sub, split, findall
from base64 import urlsafe_b64decode
from random import randint

from googleapiclient.discovery import Resource

from gmail_actions import obtener_servicio
from gmail_actions import obtener_adjuntos, listar_mensajes_por_fechas

from datetime import datetime
from zipfile import ZipFile, BadZipFile
from io import BytesIO


FORMATO_FECHA_VALIDO = '%d/%m/%Y %H:%M:%S'

ARCHIVO_ALUMNOS = 'Listado Algo I - 202101 - Regulares.csv'

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


# ---------------------------------------------------------------- #
# -------------- INICIO: INTERACCIONES/VALIDACIONES -------------- #
# ---------------------------------------------------------------- #

def validar_formato_archivo(nombre_de_archivo: str) -> 'list[str]':

    errores = list()

    partes = nombre_de_archivo.split('-')

    if len(partes) == 3:
        
        legajo = validar_numero(partes[0])

        if legajo == 0:

            errores.append('\n\t\tEl número de padrón/documento debe consistir solo en números')

    else:

        errores.append('\n\t\tNo se encontró formato {0} ó {1}'
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

        errores.append('\n\t\tNo hay extensión de archivo o es carpeta')
        errores += validar_formato_archivo(nombre_de_archivo)

    return errores


def validar_archivos_en_zip(archivo: str) -> 'list[str]':

    informe_general = []

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

    numero_formateado = sub('[a-zA-Z]+', '', numero)

    try:
        valor = int(numero_formateado)

    except ValueError:

        print('\n¡Sólo se pueden ingresar numeros!')

    return valor


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


# ---------------------------------------------------------------- #
# --------------- FIN : INTERACCIONES/VALIDACIONES --------------- #
# ---------------------------------------------------------------- #


def asignar_correctores_a_alumnos() -> 'list[dict]':

    datos = [
        'Ariadna Cattaneo', 'Aylen Reynoso', 'Bruno Lanzillota', 
        'Carolina Di Matteo', 'Daniela Palacios', 'Franco Capra',
        'Franco Lucchesi', 'Guido Costa', "Lautaro D'Abbracio", 
        'Leonel Chaves', 'Martín Sosa', 'Ramiro Esperon',
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

    columnas = ['legajo', 'apellido', 'nombre', 'entregaValida']

    informe += f"{','.join(columnas)}\n"

    for estudiante in estudiantes:

        texto = [str(estudiante.get(llave, '')) for llave in columnas]

        informe += f"{','.join(texto)}\n"

    escribir_archivo('informe_alumnos.csv', informe)

    
def normalizar_nombre_de_archivo(nombre_de_archivo: str) -> str:

    nombre_normalizado = ''

    extension = findall("\.[0-9a-z]+$", nombre_de_archivo)

    if extension:

        partes = nombre_de_archivo.split('/')

        nombre_normalizado = partes[len(partes) - 1]

    return nombre_normalizado


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


def guardar_comprimido(extension: str, carpeta: str, nombre_de_archivo: str, dato: str) -> None:

    if extension in EXTENSIONES_DE_COMPRESION:

        try:

            if extension == '.zip':

                desempaquetar_archivo_zip(carpeta, dato)

            elif extension == '.rar':
                pass

            elif extension == '7z':
                pass  
            
        except BadZipFile:
            
            archivo = urlsafe_b64decode(dato.encode('KOI8-U'))

            archivo_bytes = BytesIO(archivo)      

            objetivo = open(f'{carpeta}\\{nombre_de_archivo}', 'wb') 

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

        # Eliminamos los estudiantes que ya entregaron y está OK
        if estudiante.get('entregaValida', False):

            indice = buscar_indice_estudiante(estudiantes_actualizados, estudiante.get('legajo', 0))

            if indice != -1:

                del estudiantes_actualizados[indice]

    obtener_adjuntos_por_estudiante(servicio, estudiantes_actualizados)

    for estudiante in estudiantes:

        # De aquellos estudiantes con los que contamos con entrega pero no están OK
        # le asignamos los nuevos archivos descargados y eliminamos al mismo de la lista
        # actualizada
        if not estudiante.get('entregaValida', False):

            indice = buscar_indice_estudiante(estudiantes_actualizados, estudiante.get('legajo', 0))

            if indice != -1:

                estudiante['archivos'] = estudiantes_actualizados[indice].get('archivos', '')

                del estudiantes_actualizados[indice]

    estudiantes += estudiantes_actualizados

    generar_informe_de_entregas_validas(estudiantes)


def generar_informe_de_entregas_validas(estudiantes: 'list[dict]') -> None:

    informe_general_entregas_invalidas = ''
    informe_general_entregas_validas = ''

    for estudiante in estudiantes:

        informe_individual = list()

        if estudiante.get('archivos', '')[0].get('extension') == '.zip':

            try:

                informe_individual = validar_archivos_en_zip(
                    estudiante.get('archivos', '')[0].get('data', '')
                )

            except BadZipFile:

                informe_individual.append('Archivo "{0}": {1}\n'
                    .format(
                        estudiante.get('archivos', '')[0].get('filename', ''),
                        '\n\t\tSe cambió la extensión, no es un .zip'
                    )
                )                

        else:

            informe_individual.append('Archivo "{0}": {1}\n'
                .format(
                    estudiante.get('archivos', '')[0].get('filename', ''),
                    '\n\t\tNo es un archivo comprimido .zip'
                )
            )

        if not informe_individual:

            estudiante['entregaValida'] = True

            informe_general_entregas_validas += '{0} - {1} {2}: ENTREGA OK\n'.format(
                estudiante.get('legajo', 0),
                estudiante.get('apellido', ''),
                estudiante.get('nombre', '')               
            )

        else:
            
            informe_general_entregas_invalidas += "{0} - {1} {2}: \n".format(
                estudiante.get('legajo', 0),
                estudiante.get('apellido', ''),
                estudiante.get('nombre', '')
            )

            for error in informe_individual:

                informe_general_entregas_invalidas += f'\t{error}\n'

            informe_general_entregas_invalidas += '\n'

    escribir_archivo('entregas_invalidas.txt', informe_general_entregas_invalidas)
    escribir_archivo('entregas_validas.txt', informe_general_entregas_validas)


def obtener_adjuntos_por_estudiante(servicio: Resource, estudiantes: 'list[dict]') -> None:

    archivos = list()

    for estudiante in estudiantes:

        archivos = obtener_adjuntos(servicio, estudiante.get('mensaje', ''))

        estudiante['archivos'] = archivos


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

        estudiante['entregaValida'] = False


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

        asunto = sub('(\D+\d?\D)', '', asunto)

        legajo = validar_numero(asunto)

        legajos.append(legajo)

        mensaje['legajo'] = legajo

    legajos = list(filter(lambda i: i != 0, legajos))

    legajos_unicos = set(legajos)

    estudiantes[:] = [i for i in estudiantes if i.get('legajo', 0) in legajos_unicos]


def limpiar_mensajes_sin_adjunto(mensajes: 'list[dict]') -> None:

    for i in range(len(mensajes) - 1, 0, -1):

        partes = mensajes[i].get('payload', '').get('parts', '')[1:]

        for parte in partes:

            id_archivo_adjunto = parte.get('body', '').get('attachmentId', '')

            if not id_archivo_adjunto:

                del mensajes[i]


def convertir_dato_a_estudiante(dato: str, encabezados_de_estudiante: 'list[str]') -> dict:
    
    # PRE: 'dato', debe ser una variable de tipo str
    #      'encabezados_de_estudiante', debe ser una lista de str
    # POST: Devuelve un dict, que representa a la información pasada por 
    #       parámetro y que ha sido parseada al modelo 'estudiante'

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

    encabezados_de_estudiante = datos_no_normalizados[0:1]
    encabezados_de_estudiante = split('\,\s*|\,', encabezados_de_estudiante[0])

    datos_de_estudiantes = datos_no_normalizados[2:]
    datos_de_estudiantes = [i.title() for i in datos_de_estudiantes]

    encabezados_de_estudiante = encabezados_de_estudiante[1:2]
    encabezados_de_estudiante = [i.lower() for i in encabezados_de_estudiante]
    encabezados_de_estudiante.append('apellido')
    encabezados_de_estudiante.append('nombre')

    return encabezados_de_estudiante, datos_de_estudiantes


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


#TODO: Eliminar mensajes sin attachementId, o sea, que no enviaron archivo adjunto
def main() -> None:

    opciones = [
        "Procesar entregas y archivo de alumnos",
        "Generar informe de entregas válidas/inválidas",
        "Generar informe de entregas",
        "Asignar correctores a alumnos",
        "Guardar archivos",
        "Opción 6",
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

    while opcion != 7:

        if opcion == 1:

            # fecha_inicio, fecha_hasta = obtener_fechas()

            mensajes = listar_mensajes_por_fechas(servicio, '15/06/2021 17:00:00', '15/06/2021 21:10:00')
            # mensajes = listar_mensajes_por_fechas(servicio, fecha_inicio, fecha_hasta)

            estudiantes = procesar_informacion_de_entrada()

            limpiar_estudiantes(mensajes, estudiantes)
            limpiar_mensajes(mensajes)
            unir_mensajes_a_estudiantes(estudiantes, mensajes)

            print("\n¡Entregas y alumnos procesados!")

            flag_hay_datos = True

        elif (opcion == 2 and flag_hay_datos):

            if not flag_primera_descarga:

                obtener_adjuntos_por_estudiante(servicio, estudiantes)
                generar_informe_de_entregas_validas(estudiantes)

                flag_primera_descarga = True

            else:

                fecha_inicio, fecha_hasta = obtener_fechas()

                actualizar_entregas_e_informes(servicio, fecha_inicio, fecha_hasta, estudiantes)

            print("\n¡Informes de entregas válidas generados!")

        elif (opcion == 3 and flag_hay_datos):
            
            generar_informe_de_entregas(estudiantes)

            print("\n¡Informe de entregas generado!")

        elif (opcion == 4 and flag_hay_datos):
            
            correctores = asignar_correctores_a_alumnos()

            print("\n¡Correctores asignados!")

        elif (opcion == 5 and flag_hay_datos):

            guardar_archivos(correctores, estudiantes)

            print("\n¡Archivos guardados!")

        elif (opcion == 6):

            pass

        else:

            print("\n¡Debes procesar información primero, antes de elegir esa opción!")

        opcion = obtener_entrada_usuario(opciones)

    print("\nPrograma finalizado")


if __name__ == '__main__':
    main()