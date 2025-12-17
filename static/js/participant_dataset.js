(function(global) {
  const POSITION_LABELS = {
    player: '参赛人员',
    coach: '教练',
    trainer: '教练',
    assistant: '教练',
    medical: '医务人员',
    doctor: '医务人员',
    medic: '医务人员',
    staff: '随行人员',
    teamstaff: '随行人员'
  };

  const ROLE_PRIORITY = {
    '参赛人员': 0,
    '教练': 1,
    '医务人员': 2,
    '随行人员': 3
  };

  function safeJsonParse(value, fallback) {
    if (!value) return fallback;
    try {
      return JSON.parse(value);
    } catch (error) {
      console.warn('Failed to parse JSON from localStorage', error);
      return fallback;
    }
  }

  function readLocalList(key) {
    if (typeof localStorage === 'undefined') return [];
    return safeJsonParse(localStorage.getItem(key), []);
  }

  function collectAllTeams() {
    if (typeof localStorage === 'undefined') return [];
    const teams = [];
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key && key.startsWith('createdTeams_')) {
        const list = readLocalList(key);
        list.filter(Boolean).forEach(team => teams.push({ ...team, _source: key }));
      }
    }
    return teams;
  }

  function detectCurrentUsers() {
    if (typeof sessionStorage === 'undefined') return [];
    const keys = ['user_name', 'username', 'real_name', 'userId', 'user_id'];
    const values = keys.map(k => sessionStorage.getItem(k)).filter(Boolean);
    return Array.from(new Set(values));
  }

  function normalizeTeam(raw, source = 'local') {
    if (!raw) return null;
    const id = raw.teamId || raw.id || raw.team_id || null;
    if (!id) return null;
    return {
      id: String(id),
      teamName: raw.teamName || raw.team_name || raw.name || raw.team || '未设置',
      teamType: raw.teamType || raw.team_type || raw.type || '',
      leaderName: raw.leaderName || raw.leader_name || raw.leader || raw.contactName || '',
      leaderPhone: raw.leaderPhone || raw.leader_phone || raw.phone || raw.contactPhone || '',
      leaderEmail: raw.leaderEmail || raw.leader_email || raw.email || '',
      teamAddress: raw.teamAddress || raw.team_address || raw.address || '',
      teamDescription: raw.teamDescription || raw.team_description || raw.description || '',
      eventId: raw.eventId || raw.event_id || raw.eventID || null,
      eventName: raw.eventName || raw.event_name || '',
      submittedForReview: raw.submittedForReview || raw.submitted_for_review || raw.submitted || false,
      submittedAt: raw.submittedAt || raw.submitted_at || null,
      isCreated: raw.isCreated !== undefined ? !!raw.isCreated : true,
      source
    };
  }

  function findTeamInSnapshots(eventId, teamId) {
    if (typeof localStorage === 'undefined') return null;
    const snapshotKey = `submittedTeamData_${eventId}`;
    const snapshots = readLocalList(snapshotKey);
    if (!snapshots.length) return null;
    let target = null;
    if (teamId) {
      target = snapshots.find(item => String(getSnapshotTeamId(item)) === String(teamId)) || null;
    } else {
      target = snapshots[0] || null;
    }
    if (!target) return null;
    const normalizedTeam = normalizeTeam(target.team || { teamId: target.teamId }, 'snapshot');
    return normalizedTeam;
  }

  function getSnapshotTeamId(snapshot) {
    if (!snapshot) return null;
    return snapshot.teamId || snapshot.team_id || (snapshot.team && (snapshot.team.id || snapshot.team.teamId)) || null;
  }

  function resolveTeamContext(eventId, explicitTeamId) {
    if (!eventId) return null;
    const allTeams = collectAllTeams();

    const pickTeam = (predicate) => {
      const found = allTeams.find(predicate);
      return found ? normalizeTeam(found, found._source || 'createdTeams') : null;
    };

    if (explicitTeamId) {
      let resolved = pickTeam(team => String(team.id || team.teamId) === String(explicitTeamId));
      if (resolved) return resolved;
      const snapshotTeam = findTeamInSnapshots(eventId, explicitTeamId);
      if (snapshotTeam) return snapshotTeam;
    }

    const currentUsers = detectCurrentUsers();
    for (const user of currentUsers) {
      const userTeams = readLocalList(`createdTeams_${user}`);
      const matching = userTeams.find(team => String(team.eventId) === String(eventId) && team.isCreated === true);
      if (matching) {
        return normalizeTeam(matching, `createdTeams_${user}`);
      }
    }

    if (allTeams.length) {
      const fallback = pickTeam(team => String(team.eventId) === String(eventId));
      if (fallback) return fallback;
    }

    const applications = readLocalList('teamApplications');
    const currentUser = currentUsers[0];
    const currentUserId = sessionStorage ? (sessionStorage.getItem('user_id') || sessionStorage.getItem('userId')) : null;
    const userApplication = applications.find(app => {
      if (String(app.eventId) !== String(eventId)) return false;
      if (!(app.status === 'approved' || app.status === 'pending')) return false;
      if (currentUserId && String(app.userId) === String(currentUserId)) return true;
      if (currentUser && (app.submittedBy === currentUser || app.applicantName === currentUser)) return true;
      return false;
    });
    if (userApplication && userApplication.teamId) {
      return normalizeTeam({
        teamId: userApplication.teamId,
        teamName: userApplication.teamName || userApplication.team,
        leaderName: userApplication.teamLeader,
        eventId: userApplication.eventId,
        eventName: userApplication.eventName,
        isCreated: false
      }, 'teamApplications');
    }

    const snapshotTeam = findTeamInSnapshots(eventId, explicitTeamId || null);
    if (snapshotTeam) return snapshotTeam;

    return null;
  }

  function normalizeGender(value, idCard) {
    if (value === undefined || value === null || value === '') {
      return deriveGenderFromIdCard(idCard) || '-';
    }
    const str = String(value).toLowerCase();
    if (['男', 'male', 'm'].includes(str)) return '男';
    if (['女', 'female', 'f'].includes(str)) return '女';
    return value;
  }

  function normalizePosition(position) {
    if (!position) return POSITION_LABELS.player;
    const key = String(position).toLowerCase();
    return POSITION_LABELS[key] || position;
  }

  function deriveRoleType(position) {
    const normalized = normalizePosition(position);
    if (normalized === POSITION_LABELS.player || normalized === '参赛人员') return 'player';
    if (normalized === POSITION_LABELS.coach || normalized === '教练') return 'coach';
    if (normalized === POSITION_LABELS.medical || normalized === '医务人员') return 'medical';
    return 'staff';
  }

  function deriveGenderFromIdCard(idCard) {
    if (!idCard || idCard.length < 17) return '';
    const code = parseInt(idCard.charAt(16), 10);
    if (Number.isNaN(code)) return '';
    return code % 2 === 0 ? '女' : '男';
  }

  function calculateAgeFromIdCard(idCard) {
    if (!idCard || idCard.length < 14) return '';
    const year = parseInt(idCard.substring(6, 10), 10);
    const month = parseInt(idCard.substring(10, 12), 10) - 1;
    const day = parseInt(idCard.substring(12, 14), 10);
    if (Number.isNaN(year) || Number.isNaN(month) || Number.isNaN(day)) return '';
    const birth = new Date(year, month, day);
    const today = new Date();
    let age = today.getFullYear() - birth.getFullYear();
    const monthDiff = today.getMonth() - birth.getMonth();
    if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birth.getDate())) {
      age--;
    }
    return age >= 0 && age <= 120 ? age : '';
  }

  function maskIdCard(idCard) {
    if (!idCard || idCard.length < 8) return idCard || '-';
    return `${idCard.substring(0, 6)}****${idCard.substring(idCard.length - 4)}`;
  }

  function buildPlayerKey(name, idCard) {
    const safeName = (name || '').trim();
    const safeId = (idCard || '').trim();
    if (safeId && safeName) return `${safeId}_${safeName}`;
    if (safeId) return `${safeId}`;
    if (safeName) return `${safeName}`;
    return `anon_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
  }

  function parseSelectedEvents(raw) {
    if (!raw) return [];
    if (Array.isArray(raw)) return raw;
    if (typeof raw === 'string') {
      try {
        const parsed = JSON.parse(raw);
        if (Array.isArray(parsed)) return parsed;
        if (parsed) return [String(parsed)];
      } catch (error) {
        const text = raw.trim();
        if (!text) return [];
        if (text.includes('、')) return text.split('、').map(item => item.trim()).filter(Boolean);
        if (text.includes(',')) return text.split(',').map(item => item.trim()).filter(Boolean);
        return [text];
      }
    }
    return [];
  }

  function baseRecord(payload) {
    const idCard = payload.idCard || '';
    const derivedGender = normalizeGender(payload.gender, idCard);
    const derivedAge = payload.age || calculateAgeFromIdCard(idCard) || '';
    const normalizedPosition = normalizePosition(payload.position);
    const roleType = deriveRoleType(normalizedPosition);
    const uniqueKey = buildPlayerKey(payload.name, idCard);

    return {
      id: payload.id || payload.player_id || payload.staff_id || uniqueKey,
      uniqueKey,
      name: payload.name || payload.real_name || '未知',
      gender: derivedGender,
      age: derivedAge || '',
      idCard,
      maskedIdCard: maskIdCard(idCard),
      phone: payload.phone || '',
      teamName: payload.teamName || payload.team_name || payload.team || '',
      teamId: payload.teamId || payload.team_id || null,
      eventId: payload.eventId || payload.event_id || null,
      position: normalizedPosition,
      roleType,
      selectedEvents: parseSelectedEvents(payload.selectedEvents || payload.selected_events),
      competition_event: payload.competition_event || payload.competitionEvent || '',
      pairPartner: payload.pairPartner || payload.pair_partner_name || '',
      pairRegistered: payload.pairRegistered || payload.pair_registered || false,
      teamRegistered: payload.teamRegistered || payload.team_registered || false,
      singleRegistered: payload.singleRegistered || payload.single_registered || false,
      status: payload.status || 'registered',
      source: payload.source || 'local',
      raw: payload._raw || null
    };
  }

  function gatherFromPlayerList(eventId, teamId) {
    const list = readLocalList('playerList');
    if (!list.length) return [];
    return list.filter(player => {
      if (eventId && String(player.eventId) !== String(eventId)) return false;
      if (teamId && player.teamId && String(player.teamId) !== String(teamId)) return false;
      return true;
    }).map(player => baseRecord({
      ...player,
      idCard: player.idCard || player.id_card || player.registration_number,
      teamName: player.teamName || player.team_name,
      source: 'playerList',
      _raw: player
    }));
  }

  function gatherFromStaffList(eventId, teamId) {
    const list = readLocalList('staffList');
    if (!list.length) return [];
    return list.filter(staff => {
      if (eventId && String(staff.eventId) !== String(eventId)) return false;
      if (teamId && staff.teamId && String(staff.teamId) !== String(teamId)) return false;
      return true;
    }).map(staff => baseRecord({
      ...staff,
      idCard: staff.idCard || staff.id_card,
      teamName: staff.teamName || staff.team_name,
      source: 'staffList',
      _raw: staff
    }));
  }

  function gatherFromApplications(eventId, teamId, includePending) {
    const applications = readLocalList('teamApplications');
    if (!applications.length) return [];
    const allowedStatuses = includePending ? ['approved', 'pending'] : ['approved'];
    return applications.filter(app => {
      if (eventId && String(app.eventId) !== String(eventId)) return false;
      if (teamId && app.teamId && String(app.teamId) !== String(teamId)) return false;
      if (!allowedStatuses.includes(app.status)) return false;
      return true;
    }).map(app => baseRecord({
      ...app,
      idCard: app.applicantIdCard || app.idCard || (app.staffData && app.staffData.idCard),
      phone: app.applicantPhone || app.phone,
      name: app.applicantName || (app.staffData && (app.staffData.real_name || app.staffData.name)) || app.name,
      position: app.position || app.role || app.type,
      teamName: app.teamName || app.team,
      teamId: app.teamId,
      status: app.status,
      selectedEvents: app.selectedEvents || app.selected_events,
      source: 'teamApplications',
      _raw: app
    }));
  }

  function gatherFromSnapshotRecords(eventId, teamId) {
    if (typeof localStorage === 'undefined') return null;
    const snapshotKey = `submittedTeamData_${eventId}`;
    const snapshots = readLocalList(snapshotKey);
    if (!snapshots.length) return null;
    const matching = teamId ? snapshots.find(item => String(getSnapshotTeamId(item)) === String(teamId)) : snapshots[0];
    if (!matching) return null;
    const participants = [];
    const attachTeamId = getSnapshotTeamId(matching);

    (matching.players || []).forEach(player => {
      participants.push(baseRecord({
        ...player,
        teamId: player.teamId || attachTeamId,
        teamName: player.teamName || (matching.team && (matching.team.teamName || matching.team.name)),
        source: 'submittedSnapshot',
        _raw: player
      }));
    });

    (matching.staff || []).forEach(staff => {
      participants.push(baseRecord({
        ...staff,
        teamId: staff.teamId || attachTeamId,
        teamName: staff.teamName || (matching.team && (matching.team.teamName || matching.team.name)),
        source: 'submittedSnapshot',
        _raw: staff
      }));
    });

    return {
      team: normalizeTeam(matching.team || { teamId: attachTeamId }, 'snapshot'),
      participants
    };
  }

  function gatherFromParticipantCache(eventId, teamId) {
    if (typeof localStorage === 'undefined') return [];
    if (!eventId) return [];
    const cacheKey = `participantList_${eventId}`;
    let list = readLocalList(cacheKey);
    if (!list.length) {
      const latest = safeJsonParse(localStorage.getItem('participantList_latest'), null);
      if (latest && String(latest.eventId) === String(eventId) && Array.isArray(latest.data)) {
        list = latest.data;
      }
    }
    if (!list.length) return [];
    return list.filter(item => {
      if (eventId && String(item.eventId || item.event_id) !== String(eventId)) return false;
      if (teamId && item.teamId && String(item.teamId) !== String(teamId)) return false;
      return true;
    }).map(item => baseRecord({
      ...item,
      idCard: item.idCard || item.id_card || item.registration_number,
      teamName: item.teamName || item.team_name,
      teamId: item.teamId || item.team_id || teamId || null,
      selectedEvents: item.selectedEvents || item.selected_events,
      source: 'participantCache',
      _raw: item
    }));
  }

  function getRolePriority(record) {
    if (!record) return 99;
    const normalized = normalizePosition(record.position || record.roleType || '');
    if (Object.prototype.hasOwnProperty.call(ROLE_PRIORITY, normalized)) {
      return ROLE_PRIORITY[normalized];
    }
    if ((record.roleType || '').toLowerCase() === 'player') {
      return ROLE_PRIORITY['参赛人员'];
    }
    return 99;
  }

  function dedupeRecords(records) {
    const map = new Map();
    records.forEach(record => {
      const key = record.uniqueKey;
      const payload = { ...record };

      if (!map.has(key)) {
        map.set(key, {
          primary: payload,
          roles: [payload]
        });
        return;
      }

      const bucket = map.get(key);
      const existingPriority = getRolePriority(bucket.primary);
      const incomingPriority = getRolePriority(payload);
      const preferIncoming = incomingPriority < existingPriority;

      if (preferIncoming) {
        bucket.primary = payload;
      }

      const mergedSource = new Set(
        `${bucket.primary.source || ''},${payload.source || ''}`
          .split(',')
          .map(s => s.trim())
          .filter(Boolean)
      );
      bucket.primary.source = Array.from(mergedSource).join(',');
      bucket.primary.selectedEvents = mergeArrays(bucket.primary.selectedEvents, payload.selectedEvents);
      bucket.primary.competition_event = bucket.primary.competition_event || payload.competition_event;
      bucket.primary.pairPartner = bucket.primary.pairPartner || payload.pairPartner;
      bucket.primary.pairRegistered = bucket.primary.pairRegistered || payload.pairRegistered;
      bucket.primary.teamRegistered = bucket.primary.teamRegistered || payload.teamRegistered;
      bucket.primary.singleRegistered = bucket.primary.singleRegistered || payload.singleRegistered;

      const existsSameRole = bucket.roles.some(roleItem => normalizePosition(roleItem.position) === normalizePosition(payload.position));
      if (!existsSameRole) {
        bucket.roles.push(payload);
      }
    });

    return Array.from(map.values()).map(bucket => {
      const primary = {
        ...bucket.primary,
        isPrimaryRole: true
      };
      const extraRoles = bucket.roles
        .filter(r => r !== bucket.primary)
        .map(role => ({
          ...role,
          uniqueKey: `${role.uniqueKey}_${role.position}`,
          isPrimaryRole: false
        }));
      return [primary, ...extraRoles];
    }).flat();
  }

  function mergeArrays(a = [], b = []) {
    const set = new Set([...(a || []), ...(b || [])].filter(Boolean));
    return Array.from(set);
  }

  function sortRecords(records) {
    return records.sort((a, b) => {
      const roleDiff = (ROLE_PRIORITY[a.position] ?? ROLE_PRIORITY[a.roleType === 'player' ? '参赛人员' : a.position] ?? 99) -
        (ROLE_PRIORITY[b.position] ?? ROLE_PRIORITY[b.roleType === 'player' ? '参赛人员' : b.position] ?? 99);
      if (roleDiff !== 0) return roleDiff;
      return (a.name || '').localeCompare(b.name || '');
    });
  }

  function loadDataset(options = {}) {
    const eventId = options.eventId;
    const explicitTeamId = options.teamId !== undefined && options.teamId !== null && options.teamId !== ''
      ? String(options.teamId)
      : null;
    const includePlayers = options.includePlayers !== false;
    const includeStaff = options.includeStaff !== false;
    const includePending = options.includePending === true;
    const preferSnapshot = options.preferSnapshot === true;

    const dataset = {
      team: null,
      participants: [],
      meta: {
        total: 0,
        players: 0,
        staff: 0,
        source: preferSnapshot ? 'snapshot' : 'local'
      }
    };

    if (!eventId) {
      return dataset;
    }

    const determineBackendTeam = () => {
      if (!eventId) return null;
      if (explicitTeamId) {
        const cached = safeJsonParse(sessionStorage.getItem(`team_${explicitTeamId}`), null);
        if (cached && String(cached.event_id || cached.eventId) === String(eventId)) {
          return normalizeTeam(cached, 'backend');
        }
      }
      const key = `createdTeams_${detectCurrentUsers()[0] || ''}`;
      const candidates = readLocalList(key);
      const backendCandidate = candidates.find(item => String(item.eventId) === String(eventId) && item.isCreated === true);
      if (backendCandidate && (backendCandidate.submittedForReview || backendCandidate.submitted_for_review)) {
        return normalizeTeam(backendCandidate, 'backend');
      }
      return null;
    };

    let resolvedTeam = determineBackendTeam() || resolveTeamContext(eventId, explicitTeamId);
    dataset.team = resolvedTeam;

    let buffers = [];

    if (preferSnapshot) {
      const snapshotTargetTeamId = resolvedTeam ? resolvedTeam.id : explicitTeamId;
      const snapshotData = gatherFromSnapshotRecords(eventId, snapshotTargetTeamId);
      if (snapshotData) {
        resolvedTeam = snapshotData.team || resolvedTeam;
        dataset.team = resolvedTeam;
        buffers = buffers.concat(snapshotData.participants);
      }
    }

    const teamId = explicitTeamId || (resolvedTeam ? resolvedTeam.id : null);
    if (!dataset.team && teamId) {
      dataset.team = { id: teamId };
    }

    buffers = buffers
      .concat(gatherFromPlayerList(eventId, teamId))
      .concat(gatherFromStaffList(eventId, teamId))
      .concat(gatherFromApplications(eventId, teamId, includePending))
      .concat(gatherFromParticipantCache(eventId, teamId));

    let records = dedupeRecords(buffers);

    if (!includePlayers) {
      records = records.filter(record => record.roleType !== 'player');
    }

    if (!includeStaff) {
      records = records.filter(record => record.roleType === 'player');
    }

    records = sortRecords(records);

    dataset.participants = records;
    dataset.meta.total = records.length;
    dataset.meta.players = records.filter(r => r.roleType === 'player').length;
    dataset.meta.staff = records.length - dataset.meta.players;

    return dataset;
  }

  global.ParticipantDataset = {
    loadDataset,
    resolveTeamContext,
    maskIdCard,
    calculateAgeFromIdCard,
    normalizePosition,
    ROLE_PRIORITY
  };
})(window);
