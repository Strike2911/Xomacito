# Code signing policy

Estado: **preparación de solicitud a SignPath Foundation**, 7 de noviembre de
2026. No existe aún una aprobación, certificado o publicación firmada por este
servicio. Esta página no presenta a SignPath como patrocinador actual.

## Responsables y alcance

- Mantenedor y revisor de la integración: [Strike2911](https://github.com/Strike2911).
- Aprobador propuesto de cada solicitud de firma: Strike2911.
- Todos los participantes con acceso deberán usar autenticación multifactor en
  GitHub y SignPath. La activación de estas cuentas aún debe verificarse.
- Se firmarán solamente binarios construidos desde el código propio revisado.
  No se aplicará la identidad del proyecto a FFmpeg, Python, Qt u otras DLL/EXE
  ajenas. Los componentes redistribuidos conservarán sus avisos y firmas.
- Cada firma de producción requerirá aprobación manual en SignPath.
- Firmar no equivale a un dictamen antimalware ni garantiza reputación inmediata
  de SmartScreen. Las detecciones se investigarán con el proveedor correspondiente.

Si la solicitud es aprobada, la web y la página de descargas deberán mostrar el
crédito solicitado por el proveedor: «Free code signing provided by SignPath.io,
certificate by SignPath Foundation», con enlaces a https://signpath.io/ y
https://signpath.org/. El certificado será de la fundación, no emitido a nombre
personal del mantenedor.

## Preparación técnica incluida

- `scripts/windows_version_info.py` genera ProductName/ProductVersion coherentes
  para la aplicación y el lanzador, leyendo las versiones literales de `main.py`.
- Los specs normales de PyInstaller incluyen esos metadatos y la licencia propia.
- `signing/application.xml` restringe la firma a los dos EXE propios.
- `signing/installers.xml` restringe la firma a Setup y Update-Light de la versión
  solicitada. No se usan patrones para firmar indiscriminadamente todas las DLL.
- `.github/actions/signpath-sign` es una acción compuesta para un futuro workflow
  Windows. Sube el artefacto de la compilación a GitHub, solicita la firma, descarga
  y verifica el resultado. No se ejecuta automáticamente y no publica releases.
- `scripts/verify_signed_artifacts.ps1` exige firma Authenticode válida, sello de
  tiempo, metadatos y conjunto exacto de archivos esperados.

## Integración pendiente

1. Sincronizar el fuente íntegro de la versión que se vaya a publicar. El tag
   v4.0.47 apunta al mismo commit que contiene APP_VERSION 1.4.6; no se debe
   presentar el instalador 1.4.7 existente como resultado verificado de ese código.
2. Completar la [revisión de licencias](licensing.md) y los avisos de los binarios
   nativos concretos. La licencia MIT propia no relicencia recursos ajenos.
3. Publicar la política de privacidad y, donde corresponda, mostrarla en el
   instalador con opciones para desactivar las transferencias no solicitadas.
   No es correcto afirmar que no hay red: existen actualizaciones, búsquedas,
   descargas, modelos opcionales y cuenta/scoreboard. Deben documentarse los datos,
   servicios, conservación, controles y contacto reales, sin promesas inventadas.
4. Crear una compilación Windows íntegra en runners hospedados de GitHub:
   Python/dependencias fijadas, herramientas nativas desde fuentes verificadas con
   hashes, specs legibles, pruebas y generación de los dos EXE propios. El script
   actual espera `.tools/python311full` y `bin` locales; subir un EXE ya compilado
   o usar un runner local no satisface la verificación de origen del programa OSS.
5. Tras la aprobación de SignPath, configurar organización, proyecto, políticas,
   configuraciones XML y la identidad del aprobador. Autorizar la GitHub App sólo
   sobre Xomacito y guardar el token de envío en GitHub Secrets, nunca en el repo.
6. Firmar primero la aplicación y el lanzador. Incorporar los resultados al
   directorio de empaquetado, generar los instaladores y firmarlos después.
   Inno Setup requiere tratamiento adicional para firmar el desinstalador;
   firmar externamente Setup no firma por sí solo el EXE instalado ni unins000.exe.
7. Verificar instalación/desinstalación con protección activa, registrar los hashes
   finales y publicar sólo los archivos firmados y comprobados.

## Uso de la acción cuando la compilación Windows esté disponible

En el mismo job GitHub-hosted que produce los EXE, preparar una carpeta que
contenga únicamente `Xomacito.exe` (aplicación) y `XomacitoLauncher.exe` (lanzador).
No descargar estos archivos desde releases ni desde el equipo del mantenedor.

```yaml
- name: Firmar la aplicación y el lanzador
  uses: ./.github/actions/signpath-sign
  with:
    unsigned-directory: staging/application
    signed-directory: staging/signed-application
    phase: application
    version: '1.4.6' # utilizar la versión de main.py del commit compilado
    organization-id: ${{ vars.SIGNPATH_ORGANIZATION_ID }}
    project-slug: ${{ vars.SIGNPATH_PROJECT_SLUG }}
    signing-policy-slug: ${{ vars.SIGNPATH_SIGNING_POLICY_SLUG }}
    artifact-configuration-slug: application
    api-token: ${{ secrets.SIGNPATH_API_TOKEN }}
```

Reincorporar la aplicación a `dist/Xomacito/Xomacito.exe` y el lanzador firmado
a `Xomacito.exe` en la raíz. Después generar Setup/Update-Light y repetir con
`phase: installers`, carpeta nueva y configuración `installers`. Requerir
`actions: read` y `contents: read`. La política del servidor debe comprobar
repositorio, origen de compilación, rama aprobada y aprobación humana.

## Fuentes

- [Condiciones de la fundación](https://signpath.org/terms.html).
- [Integración con GitHub y verificación de origen](https://docs.signpath.io/trusted-build-systems/github).
- [Configuración de artefactos](https://docs.signpath.io/artifact-configuration/syntax).
- [Formulario de solicitud](https://signpath.org/apply).
