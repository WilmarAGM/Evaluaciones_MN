# Respaldos de la base de datos (VM de producción)

Instalados en la VM `evaluaciones-mn` (GCP, us-east1-b):

| Archivo | Destino en la VM |
|---|---|
| `evaluaciones-backup.sh` | `/usr/local/bin/evaluaciones-backup.sh` (root, 755) |
| `evaluaciones-backup.service` | `/etc/systemd/system/` |
| `evaluaciones-backup.timer` | `/etc/systemd/system/` |

Copias en `/var/backups/evaluaciones/`: `frecuentes/` cada 15 minutos (últimas 48 h),
`diarias/` (últimos 30 días) y `evaluaciones_latest.db`. Cada copia pasa
`PRAGMA integrity_check` antes de guardarse; si quedan menos de 1 GB libres no se copia.

Instalar o actualizar:

```sh
sudo install -m 755 evaluaciones-backup.sh /usr/local/bin/
sudo install -m 644 evaluaciones-backup.service evaluaciones-backup.timer /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now evaluaciones-backup.timer
```

Restaurar: `docker stop evaluaciones-mn`, borrar `~/app/docker_data/evaluaciones.db-wal` y `-shm`,
copiar la copia elegida sobre `~/app/docker_data/evaluaciones.db`, `docker start evaluaciones-mn`.
