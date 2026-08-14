# SSD — Clustering Distrital con Grafos (VGAE / DGI)

## Objetivo

Agrupar los distritos del Perú en clusters homogéneos por año usando representaciones aprendidas sobre grafos. La red no usa etiquetas supervisadas: aprende la estructura latente del espacio distrital combinando **features tabulares** (anemia, gasto, geografía) con **relaciones espaciales** (contigüidad distrital).

---

## Unidad de análisis

| Dimensión   | Valor                                      |
|-------------|--------------------------------------------|
| Nodo        | Un distrito (ubigeo)                       |
| Grafo       | Uno por año (2020–2025)                    |
| Nodos/grafo | ~1,889                                     |
| Aristas     | Contigüidad espacial Queen (geojson)       |

---

## Fuentes de datos

| Archivo | Uso |
|---|---|
| `data/clean/merged/panel_distrital_clean.csv` | Features de nodos |
| `notebooks/03_causal_model/cghciv.geojson` | Polígonos distritales → aristas |

---

## Construcción del grafo

### Nodos

Cada nodo `i` representa un distrito en un año dado. Sus features son las columnas numéricas del panel (normalizadas con `StandardScaler`):

```
prevalencia_anemia, gasto_total, gasto_anemia_pan,
personal_total, programa_anemia, centro_salud_municipal,
altitude, superficie, pob_densidad_2020,
pct_cultivo, pct_construido, pct_desnudo, pct_agua_visible,
n_edificios, densidad_edificios_km2,
elevacion_media, pendiente_media,
pct_agua_permanente, pct_agua_estacional
```

Los valores nulos se imputan con la mediana del año.

### Aristas — Contigüidad Queen

Una arista conecta dos distritos si sus **polígonos comparten cualquier punto de frontera**: un lado completo o incluso un solo vértice. Esto se llama contigüidad Queen (por analogía al movimiento de la reina en ajedrez, que se mueve en todas las direcciones).

```
Rook (solo lados):          Queen (lados + vértices):

  [ A ][ B ]                  [ A ][ B ]
  [ C ][ D ]                  [ C ][ D ]

  A-B, A-C, B-D, C-D          A-B, A-C, A-D, B-C, B-D, C-D
```

**¿Por qué Queen y no k-NN?**

- k-NN conecta los k distritos más cercanos por coordenada de centroide, ignorando la forma real del polígono. Puede conectar distritos que no se tocan (separados por un río, montaña, etc.) y dejar de conectar distritos que sí son vecinos si uno tiene un centroide inusualmente alejado.
- Queen usa la geometría real de los polígonos del GeoJSON, así que dos distritos son vecinos si y solo si **físicamente comparten frontera**, lo cual es la relación espacial más natural para datos distritales de salud.

**Propiedades del grafo resultante:**

| Propiedad | Valor |
|---|---|
| Tipo | No dirigido, no ponderado |
| Nodos | ~1,889 distritos |
| Grado promedio | ~5–7 vecinos por distrito |
| Islas (sin vecinos) | Muy pocas; se les agrega auto-arista como fallback |

**Implementación:**

```python
import libpysal
from torch_geometric.utils import from_scipy_sparse_matrix

w = libpysal.weights.Queen.from_dataframe(gdf)  # GeoDataFrame con polígonos
sp = w.sparse                                    # scipy sparse matrix (N×N)
edge_index, _ = from_scipy_sparse_matrix(sp)    # formato PyTorch Geometric
```

La matriz de adyacencia `sp` es simétrica: si el distrito A es vecino de B, entonces B es vecino de A. `edge_index` tiene forma `[2, num_aristas]` con los pares de nodos conectados.

> Alternativa: k-NN espacial (k=6) sobre lat/lon para nodos sin cobertura en el GeoJSON.

---

## Modelos

### Opción A — VGAE (Variational Graph Autoencoder)

**Referencia:** Kipf & Welling, 2016 (`torch_geometric.nn.VGAE`)

**Arquitectura:**

```
Encoder:
  GCNConv(n_features → 64) → ReLU
  GCNConv_mu(64 → 32)        # media del espacio latente
  GCNConv_logstd(64 → 32)    # log-desv del espacio latente

Decoder:
  InnerProductDecoder          # reconstruye A a partir de Z
```

**Loss:**

```
L = BCE(A_reconstruct, A) + KL(q(Z|X,A) || p(Z))
```

El modelo aprende a reconstruir la matriz de adyacencia, lo que fuerza a nodos vecinos a tener embeddings similares.

---

### Opción B — DGI (Deep Graph Infomax)

**Referencia:** Veličković et al., 2019 (`torch_geometric.nn.DeepGraphInfomax`)

**Arquitectura:**

```
Encoder:
  GCNConv(n_features → 512) → PReLU

Discriminator:
  Bilinear(512, 512) → sigmoid

Loss:
  Maximizar I(h_i ; s) − I(h̃_i ; s)
  donde s = readout(H) y h̃_i son embeddings de grafos corruptos
```

DGI no reconstruye aristas: aprende embeddings que maximizan la información mutua entre el embedding de cada nodo y un **resumen global** del grafo.

---

### Comparativa

| Criterio | VGAE | DGI |
|---|---|---|
| Señal de entrenamiento | Reconstrucción de A | Información mutua local-global |
| Escalabilidad | Media | Alta |
| Interpretabilidad | Espacio latente continuo (μ, σ) | Embeddings densos |
| Mejor para | Grafos con estructura de aristas fuerte | Grafos grandes, features ricas |

**Recomendación:** correr ambos y comparar la calidad de clustering.

---

## Clustering sobre embeddings

Una vez entrenado el modelo, se extraen los embeddings `Z ∈ ℝ^{N×d}` y se aplica:

1. **K-Means** con búsqueda de k óptimo (k = 3..10) por Silhouette Score
2. **Visualización:** UMAP(Z) coloreado por cluster y por `prevalencia_anemia`

---

## Evaluación

| Métrica | Descripción |
|---|---|
| Silhouette Score | Cohesión y separación de clusters en espacio latente |
| Davies-Bouldin Index | Compacidad relativa entre clusters |
| Prevalencia media por cluster | Validación epidemiológica: ¿los clusters tienen sentido clínico? |
| Mapa coroplético | Visualización geográfica de los clusters por año |

---

## Pipeline

```
panel_distrital_clean.csv
        │
        ▼
[1] Construcción del grafo por año
    - Nodos: features normalizadas
    - Aristas: Queen contiguity (geojson)
        │
        ▼
[2] Entrenamiento VGAE / DGI
    - Por año o sobre todos los años concatenados
        │
        ▼
[3] Extracción de embeddings Z
        │
        ▼
[4] K-Means → asignación de clusters
        │
        ▼
[5] Evaluación + visualización
    - Silhouette, mapa distrital, UMAP
```

---

## Dependencias adicionales

```bash
pip install torch-geometric libpysal umap-learn
```

---

## Archivo de implementación

`notebooks/04_graph_clustering/00_vgae_dgi_clustering.ipynb`
