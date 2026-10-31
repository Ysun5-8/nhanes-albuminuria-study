-- Add predictors without dropping adults who have missing measurements.
WITH bp_values AS (
    SELECT SEQN,
        (COALESCE(BPXOSY1,0)+COALESCE(BPXOSY2,0)+COALESCE(BPXOSY3,0)) /
        NULLIF(1.0*((BPXOSY1 IS NOT NULL)+(BPXOSY2 IS NOT NULL)+(BPXOSY3 IS NOT NULL)),0) AS systolic,
        (COALESCE(BPXODI1,0)+COALESCE(BPXODI2,0)+COALESCE(BPXODI3,0)) /
        NULLIF(1.0*((BPXODI1 IS NOT NULL)+(BPXODI2 IS NOT NULL)+(BPXODI3 IS NOT NULL)),0) AS diastolic
    FROM blood_pressure
)
SELECT p.SEQN, p.WTMEC2YR, p.SDMVSTRA, p.SDMVPSU,
       p.raw_positive AS raw_label, p.adjusted_positive AS converted_label,
       p.RIDAGEYR AS age,
       CASE p.RIAGENDR WHEN 1 THEN 'male' WHEN 2 THEN 'female' END AS sex,
       b.BMXBMI AS bmi, bp.systolic, bp.diastolic,
       CASE d.DIQ010 WHEN 1 THEN 'yes' WHEN 2 THEN 'no'
                    WHEN 3 THEN 'borderline' END AS diabetes,
       CASE WHEN s.SMQ020 = 2 THEN 'never'
            WHEN s.SMQ020 = 1 AND s.SMQ040 = 3 THEN 'former'
            WHEN s.SMQ020 = 1 AND s.SMQ040 IN (1,2) THEN 'current'
       END AS smoking
FROM participants p
LEFT JOIN body_measures b ON p.SEQN = b.SEQN
LEFT JOIN bp_values bp ON p.SEQN = bp.SEQN
LEFT JOIN diabetes_history d ON p.SEQN = d.SEQN
LEFT JOIN smoking_history s ON p.SEQN = s.SEQN
WHERE p.complete_adult
ORDER BY p.SEQN;
