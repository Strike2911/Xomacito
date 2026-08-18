# Flujo de desarrollo y ofuscacion

La rama `desarrollo` es la fuente mantenible y sin ofuscar. Las funciones nuevas deben entrar ahi primero.

La rama `ofuscado` se regenera desde `desarrollo` y queda con esta forma:

1. Todo el historial de `desarrollo`.
2. Un solo commit adicional con `main.py`, `launcher.py` y `src/**/*.py` ofuscados.

Para regenerarla despues de cada commit en `desarrollo`:

```powershell
.\scripts\update_obfuscated_branch.ps1
```

Para regenerarla y publicarla en GitHub:

```powershell
.\scripts\update_obfuscated_branch.ps1 -Push
```

El script mueve `ofuscado` al ultimo commit de `desarrollo`, ejecuta la ofuscacion y crea un commit nuevo. Si se usa `-Push`, publica con `--force-with-lease` para sustituir el commit ofuscado anterior sin borrar cambios remotos inesperados.

No desarrolles sobre `ofuscado`; esa rama es salida generada.
