queries = {
    'existed':          'SELECT EXISTS(SELECT 1 FROM profile3 WHERE "user"=$1);',
    'profile_new':      'INSERT INTO profile3 ("user", race, classes, guild, raidstats, dt) VALUES ($1, $2, $3, $4, $5, $6);',
    'profile_update':   'UPDATE profile3 SET race=$2, classes=$3, guild=$4, raidstats=$5, dt=$6 WHERE "user"=$1;',
    'weapon_new':       'INSERT INTO profile3 ("user", raidstats, weapon, wt) VALUES ($1, $2, $3, $4);',
    'weapon_update':    'UPDATE profile3 SET raidstats=$2, weapon=$3, wt=$4 WHERE "user"=$1;',
    'adv_new':          'INSERT INTO profile3 ("user", xp, adv, at) VALUES ($1, $2, $3, $4);',
    'adv_update':       'UPDATE profile3 SET xp=$2, adv=$3, at=$4 WHERE "user"=$1;',
    'fetch_weapons':    'SELECT weapon FROM profile3 WHERE "user"=$1',
    'new_weapons':      'INSERT INTO profile3 ("user", race, classes, guild, raidstats, weapon, dt, wt) VALUES ($1, $2, $3, $4, $5, $6, $7, $7);',
    'update_weapons':   'UPDATE profile3 SET race=$2, classes=$3, guild=$4, raidstats=$5, weapon=$6, dt=$7, wt=$7 WHERE "user"=$1;',
    'fetch_user':       'SELECT * FROM profile3 WHERE "user"=$1',
}