{#
  Thin pass-through over the table jobs/pca_curve_factors.py writes — see
  gold_sources.yml. Not a transformation; exists so PCA shows up in dbt's
  lineage/docs even though dbt itself never computes it.
#}

select
    observation_date,
    pc1_level,
    pc2_slope,
    pc3_curvature,
    explained_variance_ratio_pc1,
    explained_variance_ratio_pc2,
    explained_variance_ratio_pc3
from {{ source('gold_py', 'pca_curve_factors_raw') }}
