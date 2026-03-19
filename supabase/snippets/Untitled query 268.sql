SELECT
  s.id          AS school_id,
  s.school      AS school_name,
  s.city,
  s.state,
  s.zip_code,
  STRING_AGG(c.name, ', ' ORDER BY c.name) AS cohorts
FROM public.schools s
LEFT JOIN public.schools_cohorts j ON j.schools_id = s.id
LEFT JOIN public.cohorts c ON c.id = j.cohorts_id
WHERE UPPER(TRIM(s.state)) = 'CA'
GROUP BY s.id, s.school, s.city, s.state, s.zip_code
ORDER BY s.school;