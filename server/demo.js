// "npm run demo": live a pretend day quickly, without the API, so there is something to look at.
// It fills the database with instinct-driven activity, then exits. Run "npm start" afterwards.
process.env.MEMO_DEMO = '1';
const { seedWorld } = await import('./world.js');
const { seedApps, scanBooks } = await import('./computer.js');
const { heartbeat } = await import('./brain.js');
seedWorld(); seedApps(); scanBooks();
for (let i = 0; i < 40; i++) await heartbeat(true);
console.log('Ash has lived a pretend day. Run "npm start" to see what he did.');
