const { PrismaClient } = require('@prisma/client');
const prisma = new PrismaClient();

async function main() {
  const users = await prisma.user.findMany();
  console.log("Users in SQLite DB:", users.length);
  console.log(users.map(u => ({ email: u.email, role: u.role })));
}

main().catch(console.error).finally(() => prisma.$disconnect());
