queries = {
    'existed':          'SELECT EXISTS(SELECT 1 FROM profile3 WHERE uid=$1);',
    'profile_update':   'INSERT INTO profile3 (uid, race, classes, guild, raidstats, dt) VALUES ($1, $2, $3, $4, $5, $6) ON CONFLICT (uid) DO UPDATE SET race=$2, classes=$3, guild=$4, raidstats=$5, dt=$6;',
    'adv_update':       'INSERT INTO profile3 (uid, xp, adv, at) VALUES ($1, $2, $3, $4) ON CONFLICT (uid) DO UPDATE SET xp=$2, adv=$3, at=$4;',
    'fetch_weapons':    'SELECT weapon FROM profile3 WHERE uid=$1',
    'update_weapons':   'INSERT INTO profile3 (uid, race, classes, guild, raidstats, weapon, dt, wt) VALUES ($1, $2, $3, $4, $5, $6, $7, $7) ON CONFLICT (uid) DO UPDATE SET race=$2, classes=$3, guild=$4, raidstats=$5, weapon=$6, dt=$7, wt=$7;',
    'fetch_user':       'SELECT * FROM profile3 WHERE uid=$1',
    'fetch_profile':    'SELECT race, classes, weapon, raidstats FROM profile3 WHERE uid=$1',
    'fetch_guild':      'SELECT guild FROM profile3 WHERE uid=$1',
}