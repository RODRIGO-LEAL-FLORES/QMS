# Guía de permisos por módulo

Este documento describe los permisos asignables a cada rol en QMS. Los permisos se asignan al **rol** y se aplican a todos los usuarios que lo tienen. El sistema autoriza con los permisos estándar de Django; los antiguos indicadores booleanos por usuario ya no se utilizan.

## Cómo leer los permisos

Para cada submódulo, Django crea normalmente estas cuatro acciones:

- **Agregar** (`add_<modelo>`): crear registros.
- **Editar** (`change_<modelo>`): modificar registros existentes.
- **Eliminar** (`delete_<modelo>`): borrar registros.
- **Consultar** (`view_<modelo>`): entrar y consultar la información del submódulo.

Las acciones son independientes. Tener **Consultar** no concede Agregar, Editar ni Eliminar; tener una acción de edición tampoco concede automáticamente las otras. Algunas pantallas tienen permisos especiales descritos abajo.

Los permisos pertenecen al modelo y módulo donde se definió la información, no necesariamente al menú desde el que se consulta. Por ejemplo, **Tipos de laminación** pertenece a Liberaciones y **Tipos de acero** pertenece a Scrap; una pantalla de otro módulo puede utilizar esos mismos catálogos sin cambiar quién es dueño del permiso.

## Áreas

Submódulo **Área**: Agregar, Editar, Eliminar y Consultar áreas del sistema. Las áreas se usan, entre otras cosas, para asignar usuarios y organizar responsabilidades.

## Clientes

Submódulo **Cliente**: Agregar, Editar, Eliminar y Consultar el catálogo de clientes, utilizado por liberaciones, Scrap y Tarjetas Viajeras.

## Liberaciones

Cada submódulo tiene las cuatro acciones estándar:

- **Estatus**: administrar los estados disponibles para las liberaciones.
- **Liberación**: registrar y administrar liberaciones.
- **Máquinas**: administrar las máquinas y líneas utilizadas.
- **Tipos de laminación**: administrar el catálogo de laminaciones. Este permiso también puede ser necesario desde otros módulos que usan dicho catálogo.
- **Tiras de liberación**: administrar y consultar las tiras asociadas con liberaciones.

## Reclamaciones

Cada submódulo tiene Agregar, Editar, Eliminar y Consultar:

- **Categoría**: clasificar las reclamaciones.
- **Defecto**: administrar los tipos de defecto.
- **Estatus**: mantener los estados del flujo de reclamaciones.
- **Ocurrencia**: administrar las ocurrencias relacionadas con una reclamación.
- **Reclamación**: administrar los registros principales de reclamaciones.

Permiso especial:

- **Consultar reportes** (`view_reportes`): acceder a los reportes de reclamaciones. No equivale a consultar el listado de reclamaciones.

## Reclamaciones internas

Cada submódulo cuenta con Agregar, Editar, Eliminar y Consultar:

- **Estatus**: administrar los estados del proceso interno.
- **Evidencias**: administrar las evidencias adjuntas.
- **Formato oficial**: consultar y administrar el formato oficial.
- **Prioridad**: administrar los niveles de prioridad.
- **Reclamación interna**: administrar los registros principales de reclamaciones internas.

Permisos especiales:

- **Consultar reportes** (`view_reportes`): acceder a los reportes de reclamaciones internas.
- **Eliminar formatos** (`delete_formatoreclamacioninterna`): eliminar el formato oficial. Es independiente de eliminar reclamaciones internas.

## Scrap

Cada submódulo cuenta con Agregar, Editar, Eliminar y Consultar:

- **Clasificaciones**: administrar las clasificaciones de Scrap.
- **Defectos**: administrar el catálogo de defectos.
- **Operadores**: administrar operadores.
- **Registros de Scrap**: consultar y administrar los registros.
- **Supervisores**: administrar supervisores.
- **Tipos de acero**: administrar el catálogo de aceros. Otros módulos pueden utilizarlo, pero el permiso del catálogo sigue perteneciendo a Scrap.
- **Tipos de pieza**: administrar el catálogo de piezas.
- **Turnos**: administrar los turnos.

Permisos especiales del submódulo **Registros de Scrap**:

- **Consultar producción** (`view_produccion_scrap`): consultar la información de Scrap de producción.
- **Editar producción** (`change_produccion_scrap`): actualizar los datos de producción de Scrap.
- **Exportar registros** (`export_scrap`): exportar información de Scrap. No se concede por tener Consultar.

## Tarjetas Viajeras

Submódulos con las cuatro acciones estándar:

- **Configuración de piezas**: administrar configuraciones de piezas por alambre.
- **Espesores**: administrar el catálogo de espesores.
- **Números de parte**: administrar números de parte de cliente.
- **Producción**: administrar órdenes y registros de producción.
- **Reasignación de tarjetas**: consultar y administrar la reasignación entre producciones, según la acción asignada.
- **Estatus de tarjetas**: administrar los estados disponibles.
- **Tarjeta viajera**: consultar y administrar las tarjetas.

Permisos especiales del submódulo **Tarjeta viajera**:

- **Imprimir tarjetas** (`print_tarjetaviajera`): imprimir tarjetas y etiquetas.
- **Actualizar estatus** (`update_status_tarjetaviajera`): cambiar únicamente el estatus de una tarjeta.
- **Actualizar medidas** (`update_measurements_tarjetaviajera`): actualizar medidas de la tarjeta, como alambres, piezas por alambre, peso y tara.

Estos permisos especiales no son equivalentes entre sí ni sustituyen automáticamente Agregar, Editar o Eliminar.

## Usuarios

- **Roles**: Agregar, Editar, Eliminar y Consultar roles. Administrar un rol permite modificar el conjunto de permisos que recibirán sus usuarios.
- **Usuarios**: Agregar, Editar, Eliminar y Consultar usuarios. La edición de un usuario permite asignarle un rol y, cuando corresponda, un área; los permisos se configuran en el rol, no en casillas individuales del usuario.

## Recomendación para configurar un rol

1. Activa **Consultar** en cada submódulo al que deba poder entrar el rol.
2. Activa por separado solo las acciones que necesite realizar.
3. Revisa los permisos especiales cuando requiera reportes, exportaciones, impresión, actualización de estatus o actualización de medidas.
4. Si una pantalla usa un catálogo perteneciente a otro módulo, concede el permiso del modelo propietario de ese catálogo.
