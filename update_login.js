const fs = require('fs');
const path = 'frontend/src/pages/Login.jsx';
let content = fs.readFileSync(path, 'utf8');

const oldCode = `      if (res.ok) {
        if (isRegister) {
          setIsRegister(false);
          setError('');
          alert('Compte créé avec succès ! Vous pouvez maintenant vous connecter.');
        } else {
          localStorage.setItem('token', data.access_token);
          localStorage.setItem('role', data.role);
          navigate('/account');
        }`;

const newCode = `      if (res.ok) {
        if (isRegister) {
          // Auto-login after register
          const loginRes = await fetch(\`\${baseUrl}/api/auth/login\`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
          });
          
          if (loginRes.ok) {
            const loginData = await loginRes.json();
            localStorage.setItem('token', loginData.access_token);
            localStorage.setItem('role', loginData.role);
            navigate('/account');
          } else {
            setIsRegister(false);
            setError('Compte créé, mais erreur de connexion automatique.');
          }
        } else {
          localStorage.setItem('token', data.access_token);
          localStorage.setItem('role', data.role);
          navigate('/account');
        }`;

content = content.replace(oldCode, newCode);
fs.writeFileSync(path, content, 'utf8');
console.log('Login.jsx updated');
