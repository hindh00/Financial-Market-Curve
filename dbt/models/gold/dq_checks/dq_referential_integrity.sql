select
    'referential_integrity' as check_name,
    f.observation_date,
    f.series_id,
    f.tenor,
    cast(null as date) as pull_date,
    case when s.series_id is null or d.date_day is null then 'fail' else 'pass' end as status,
    'high' as severity,
    'fact_observation row does not match a dim_series or dim_date row' as details
from {{ ref('fact_observation') }} f
left join {{ ref('dim_series') }} s
    on f.series_id = s.series_id
left join {{ ref('dim_date') }} d
    on f.observation_date = d.date_day
