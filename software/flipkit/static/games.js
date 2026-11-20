/* FlipKit Games */
!function(){
'use strict';
var G=window.FK_GAMES={};
function cv(el,w,h){el.innerHTML='';var c=document.createElement('canvas');c.width=w;c.height=h;c.style.cssText='display:block;max-width:100%;margin:0 auto;background:#050a10;border:1px solid rgba(255,255,255,.08);border-radius:4px;';el.appendChild(c);return c;}
function lbl(el,t){el.insertAdjacentHTML('beforeend','<p style="text-align:center;font-size:9px;color:rgba(255,255,255,.2);margin:4px 0 0;font-family:monospace">'+t+'</p>');}
function rnd(n){return Math.floor(Math.random()*n);}
function domGame(el,html){el.innerHTML='<div style="font-family:monospace;color:rgba(255,255,255,.7);padding:8px">'+html+'</div>';}

/* SNAKE */
G.snake={title:'Snake',cat:'arcade',render:function(el){
  var C=cv(el,300,300),x=C.getContext('2d'),N=20,S=15,sn,dir,nd,food,sc,iv;
  function init(){sn=[{x:10,y:10}];dir={x:1,y:0};nd=null;sc=0;food=rf();clearInterval(iv);iv=setInterval(tick,110);}
  function rf(){return{x:rnd(N),y:rnd(N)};}
  function tick(){if(nd){dir=nd;nd=null;}var h=sn[0],n={x:h.x+dir.x,y:h.y+dir.y};
    if(n.x<0||n.x>=N||n.y<0||n.y>=N||sn.some(function(s){return s.x===n.x&&s.y===n.y;})){clearInterval(iv);draw(1);return;}
    sn.unshift(n);if(n.x===food.x&&n.y===food.y){sc++;food=rf();}else sn.pop();draw(0);}
  function draw(dead){x.fillStyle='#050a10';x.fillRect(0,0,300,300);
    sn.forEach(function(s,i){x.fillStyle=i?'#15a060':'#1FCC7C';x.fillRect(s.x*S+1,s.y*S+1,S-2,S-2);});
    x.fillStyle='#FF5F5F';x.fillRect(food.x*S+3,food.y*S+3,S-6,S-6);
    x.fillStyle='rgba(255,255,255,.4)';x.font='10px monospace';x.fillText('Score:'+sc,4,296);
    if(dead){x.fillStyle='rgba(0,0,0,.8)';x.fillRect(50,110,200,70);x.fillStyle='#1FCC7C';x.font='bold 14px monospace';x.textAlign='center';x.fillText('GAME OVER',150,142);x.fillStyle='rgba(255,255,255,.5)';x.font='10px monospace';x.fillText('Score:'+sc+' · SPACE',150,162);x.textAlign='left';}}
  var km={ArrowUp:{x:0,y:-1},ArrowDown:{x:0,y:1},ArrowLeft:{x:-1,y:0},ArrowRight:{x:1,y:0},KeyW:{x:0,y:-1},KeyS:{x:0,y:1},KeyA:{x:-1,y:0},KeyD:{x:1,y:0}};
  function kd(e){var d=km[e.code];if(d&&!(d.x===-dir.x&&d.y===-dir.y)){nd=d;e.preventDefault();}if(e.code==='Space')init();}
  document.addEventListener('keydown',kd);el._fkCleanup=function(){clearInterval(iv);document.removeEventListener('keydown',kd);};
  init();lbl(el,'ARROWS/WASD · SPACE restart');
}};

/* PONG */
G.pong={title:'Pong',cat:'board',render:function(el){
  var C=cv(el,400,280),x=C.getContext('2d'),W=400,H=280;
  var p1={y:H/2-30,s:0},p2={y:H/2-30,s:0},b={x:W/2,y:H/2,vx:3,vy:2},PH=60,PW=8,iv;
  function tick(){
    b.x+=b.vx;b.y+=b.vy;
    if(b.y<=0||b.y>=H)b.vy*=-1;
    if(b.x<=20&&b.y>=p1.y&&b.y<=p1.y+PH){b.vx=Math.abs(b.vx);b.vy+=(b.y-p1.y-PH/2)*0.1;}
    if(b.x>=W-20&&b.y>=p2.y&&b.y<=p2.y+PH){b.vx=-Math.abs(b.vx);b.vy+=(b.y-p2.y-PH/2)*0.1;}
    if(b.x<0){p2.s++;reset();}if(b.x>W){p1.s++;reset();}
    p2.y+=(b.y-p2.y-PH/2)*0.06;p2.y=Math.max(0,Math.min(H-PH,p2.y));draw();}
  function reset(){b.x=W/2;b.y=H/2;b.vx=(rnd(2)?3:-3);b.vy=(rnd(2)?2:-2);}
  function draw(){x.fillStyle='#050a10';x.fillRect(0,0,W,H);
    x.strokeStyle='rgba(255,255,255,.08)';x.setLineDash([6,6]);x.beginPath();x.moveTo(W/2,0);x.lineTo(W/2,H);x.stroke();x.setLineDash([]);
    x.fillStyle='#1FCC7C';x.fillRect(12,p1.y,PW,PH);x.fillRect(W-20,p2.y,PW,PH);
    x.fillStyle='#fff';x.beginPath();x.arc(b.x,b.y,5,0,6.28);x.fill();
    x.fillStyle='rgba(255,255,255,.6)';x.font='20px monospace';x.textAlign='center';x.fillText(p1.s,W/2-40,30);x.fillText(p2.s,W/2+40,30);x.textAlign='left';}
  var keys={};
  function kd(e){keys[e.code]=1;if(['ArrowUp','ArrowDown'].includes(e.code))e.preventDefault();}
  function ku(e){delete keys[e.code];}
  document.addEventListener('keydown',kd);document.addEventListener('keyup',ku);
  iv=setInterval(function(){if(keys.ArrowUp)p1.y=Math.max(0,p1.y-5);if(keys.ArrowDown)p1.y=Math.min(H-PH,p1.y+5);tick();},16);
  el._fkCleanup=function(){clearInterval(iv);document.removeEventListener('keydown',kd);document.removeEventListener('keyup',ku);};
  lbl(el,'↑↓ move · CPU is right paddle');
}};

/* BREAKOUT */
G.breakout={title:'Breakout',cat:'arcade',render:function(el){
  var C=cv(el,360,300),x=C.getContext('2d'),W=360,H=300;
  var px=W/2-30,pw=60,py=H-20,bx=W/2,by=H-40,vx=2.5,vy=-3,bricks=[],score=0,lives=3,iv;
  for(var r=0;r<5;r++)for(var c=0;c<9;c++)bricks.push({x:c*38+6,y:r*22+30,w:34,h:18,alive:1,color:['#FF5F5F','#F5A623','#1FCC7C','#4FC3F7','#CE93D8'][r]});
  function tick(){bx+=vx;by+=vy;if(bx<5||bx>W-5)vx*=-1;if(by<5)vy*=-1;
    if(by>py-5&&bx>=px&&bx<=px+pw){vy=-Math.abs(vy);vx+=((bx-px-pw/2)/pw)*2;}
    if(by>H+10){lives--;by=H-40;bx=W/2;vy=-3;if(lives<=0){clearInterval(iv);draw(1);return;}}
    bricks.forEach(function(b){if(!b.alive)return;if(bx>=b.x&&bx<=b.x+b.w&&by>=b.y&&by<=b.y+b.h){b.alive=0;vy*=-1;score+=10;}});
    if(!bricks.some(function(b){return b.alive;})){clearInterval(iv);draw(2);return;}draw(0);}
  function draw(end){x.fillStyle='#050a10';x.fillRect(0,0,W,H);
    bricks.forEach(function(b){if(!b.alive)return;x.fillStyle=b.color;x.fillRect(b.x,b.y,b.w,b.h);});
    x.fillStyle='#1FCC7C';x.fillRect(px,py,pw,8);
    x.fillStyle='#fff';x.beginPath();x.arc(bx,by,5,0,6.28);x.fill();
    x.fillStyle='rgba(255,255,255,.4)';x.font='10px monospace';x.fillText('Score:'+score+' Lives:'+lives,4,20);
    if(end){x.fillStyle='rgba(0,0,0,.8)';x.fillRect(80,110,200,70);x.fillStyle=end===2?'#1FCC7C':'#FF5F5F';x.font='bold 14px monospace';x.textAlign='center';x.fillText(end===2?'YOU WIN!':'GAME OVER',W/2,145);x.fillStyle='rgba(255,255,255,.5)';x.font='10px monospace';x.fillText('Score:'+score,W/2,165);x.textAlign='left';}}
  var keys={};
  function kd(e){keys[e.code]=1;if(['ArrowLeft','ArrowRight'].includes(e.code))e.preventDefault();}
  function ku(e){delete keys[e.code];}
  document.addEventListener('keydown',kd);document.addEventListener('keyup',ku);
  iv=setInterval(function(){if(keys.ArrowLeft)px=Math.max(0,px-6);if(keys.ArrowRight)px=Math.min(W-pw,px+6);tick();},16);
  el._fkCleanup=function(){clearInterval(iv);document.removeEventListener('keydown',kd);document.removeEventListener('keyup',ku);};
  lbl(el,'←→ move paddle');
}};

/* FLAPPY */
G.flappy={title:'Flappy Bird',cat:'arcade',render:function(el){
  var C=cv(el,300,360),x=C.getContext('2d'),W=300,H=360;
  var by=H/2,bvy=0,pipes=[],sc=0,state=0,iv;
  function newPipe(){var gap=100,gy=60+rnd(H-160);return{x:W,top:gy,bot:gy+gap};}
  function init(){by=H/2;bvy=0;pipes=[newPipe()];sc=0;state=1;}
  function tick(){if(state!==1)return;
    bvy+=0.4;by+=bvy;
    pipes.forEach(function(p){p.x-=2.5;});
    if(pipes[pipes.length-1].x<W-160)pipes.push(newPipe());
    pipes=pipes.filter(function(p){return p.x>-20;});
    pipes.forEach(function(p){if(p.x<30&&p.x>10)sc++;});
    if(by>H-10||by<0){state=2;clearInterval(iv);draw();}
    pipes.forEach(function(p){if(30>p.x-10&&30<p.x+20&&(by<p.top||by>p.bot)){state=2;clearInterval(iv);}});
    draw();}
  function draw(){x.fillStyle='#050a10';x.fillRect(0,0,W,H);
    pipes.forEach(function(p){x.fillStyle='#15a060';x.fillRect(p.x-10,0,20,p.top);x.fillRect(p.x-10,p.bot,20,H-p.bot);});
    x.fillStyle='#F5A623';x.beginPath();x.arc(30,by,10,0,6.28);x.fill();
    x.fillStyle='rgba(255,255,255,.5)';x.font='14px monospace';x.textAlign='center';x.fillText(sc,W/2,25);x.textAlign='left';
    if(state===0){x.fillStyle='rgba(255,255,255,.5)';x.font='11px monospace';x.textAlign='center';x.fillText('SPACE to start',W/2,H/2);x.textAlign='left';}
    if(state===2){x.fillStyle='rgba(0,0,0,.8)';x.fillRect(60,140,180,70);x.fillStyle='#FF5F5F';x.font='bold 14px monospace';x.textAlign='center';x.fillText('GAME OVER',W/2,170);x.fillStyle='rgba(255,255,255,.5)';x.font='10px monospace';x.fillText('Score:'+sc+' · SPACE',W/2,190);x.textAlign='left';}}
  function kd(e){if(e.code==='Space'){e.preventDefault();if(state===0){init();clearInterval(iv);iv=setInterval(tick,16);}else if(state===1){bvy=-7;}else if(state===2){init();clearInterval(iv);iv=setInterval(tick,16);}}}
  document.addEventListener('keydown',kd);C.addEventListener('click',function(){if(state===0){init();clearInterval(iv);iv=setInterval(tick,16);}else if(state===1)bvy=-7;});
  el._fkCleanup=function(){clearInterval(iv);document.removeEventListener('keydown',kd);};
  draw();lbl(el,'SPACE or tap to flap');
}};

/* SIMON */
G.simon={title:'Simon',cat:'arcade',render:function(el){
  var C=cv(el,300,300),x=C.getContext('2d'),COLS=['#FF5F5F','#1FCC7C','#F5A623','#4FC3F7'],seq=[],pidx=0,lit=-1,score=0,state='idle';
  function seg(i){var a=[Math.PI,1.5*Math.PI,0,0.5*Math.PI][i],b=a+Math.PI/2;x.beginPath();x.moveTo(150,150);x.arc(150,150,120,a,b);x.closePath();}
  function draw(){x.fillStyle='#050a10';x.fillRect(0,0,300,300);
    for(var i=0;i<4;i++){x.fillStyle=lit===i?COLS[i]:COLS[i]+'44';seg(i);x.fill();}
    x.fillStyle='#050a10';x.beginPath();x.arc(150,150,45,0,6.28);x.fill();
    x.fillStyle='rgba(255,255,255,.5)';x.font='12px monospace';x.textAlign='center';
    x.fillText(state==='idle'?'Click to start':state==='show'?'Watch...':'Score:'+score,150,155);x.textAlign='left';}
  function flash(i,cb){lit=i;draw();setTimeout(function(){lit=-1;draw();setTimeout(cb,200);},400);}
  function showSeq(idx){if(idx>=seq.length){state='input';pidx=0;draw();return;}flash(seq[idx],function(){showSeq(idx+1);});}
  function start(){seq=[rnd(4)];score=0;state='show';draw();setTimeout(function(){showSeq(0);},600);}
  C.addEventListener('click',function(e){
    if(state==='idle'){start();return;}
    if(state!=='input')return;
    var r=C.getBoundingClientRect(),mx=e.clientX-r.left,my=e.clientY-r.top;
    var dx=mx-150,dy=my-150;if(Math.sqrt(dx*dx+dy*dy)>120||Math.sqrt(dx*dx+dy*dy)<45)return;
    var ang=Math.atan2(dy,dx);if(ang<0)ang+=2*Math.PI;
    var btn=Math.floor(((ang+Math.PI/2)%(2*Math.PI))/(Math.PI/2))%4;
    var order=[2,0,3,1];btn=order[btn];
    flash(btn,function(){
      if(btn===seq[pidx]){pidx++;if(pidx===seq.length){score++;seq.push(rnd(4));state='show';setTimeout(function(){showSeq(0);},600);}
      }else{state='idle';draw();}});});
  draw();lbl(el,'Repeat the colour sequence');
}};

/* TETRIS */
G.tetris={title:'Tetris',cat:'puzzle',render:function(el){
  var C=cv(el,220,440),x=C.getContext('2d'),W=10,H=20,SZ=22;
  var PIECES=[[[1,1,1,1]],[[1,1],[1,1]],[[0,1,0],[1,1,1]],[[1,0,0],[1,1,1]],[[0,0,1],[1,1,1]],[[0,1,1],[1,1,0]],[[1,1,0],[0,1,1]]];
  var COLORS=['#4FC3F7','#F9E04B','#CE93D8','#FF8A65','#4DB6AC','#1FCC7C','#FF5F5F'];
  var board,piece,px,py,score,iv;
  function newBoard(){board=[];for(var i=0;i<H;i++)board.push(new Array(W).fill(0));}
  function newPiece(){var t=rnd(7);piece=PIECES[t];px=Math.floor(W/2-piece[0].length/2);py=0;return !collide(px,py,piece);}
  function rotate(p){return p[0].map(function(_,i){return p.map(function(r){return r[i];}).reverse();});}
  function collide(nx,ny,np){return np.some(function(r,ri){return r.some(function(c,ci){return c&&(nx+ci<0||nx+ci>=W||ny+ri>=H||(board[ny+ri]&&board[ny+ri][nx+ci]));});});}
  function lock(){piece.forEach(function(r,ri){r.forEach(function(c,ci){if(c)board[py+ri][px+ci]=1+PIECES.indexOf(piece)%7;});});
    var cleared=0;board=board.filter(function(r){if(r.every(function(c){return c;})){cleared++;return false;}return true;});
    while(board.length<H)board.unshift(new Array(W).fill(0));score+=cleared*100;}
  function tick(){if(!collide(px,py+1,piece))py++;else{lock();if(!newPiece()){clearInterval(iv);draw(1);}}draw(0);}
  function draw(over){x.fillStyle='#050a10';x.fillRect(0,0,220,440);
    board.forEach(function(r,ri){r.forEach(function(c,ci){if(c){x.fillStyle=COLORS[(c-1)%7];x.fillRect(ci*SZ+1,ri*SZ+1,SZ-2,SZ-2);}});});
    piece.forEach(function(r,ri){r.forEach(function(c,ci){if(c){x.fillStyle=COLORS[rnd(7)];x.fillStyle=COLORS[PIECES.indexOf(piece)%7];x.fillRect((px+ci)*SZ+1,(py+ri)*SZ+1,SZ-2,SZ-2);}});});
    x.fillStyle='rgba(255,255,255,.4)';x.font='10px monospace';x.fillText('Score:'+score,4,435);
    if(over){x.fillStyle='rgba(0,0,0,.85)';x.fillRect(20,170,180,60);x.fillStyle='#FF5F5F';x.font='bold 13px monospace';x.textAlign='center';x.fillText('GAME OVER',110,197);x.fillStyle='rgba(255,255,255,.5)';x.font='10px monospace';x.fillText('Score:'+score,110,215);x.textAlign='left';}}
  function kd(e){
    if(e.code==='ArrowLeft'&&!collide(px-1,py,piece)){px--;draw(0);}
    if(e.code==='ArrowRight'&&!collide(px+1,py,piece)){px++;draw(0);}
    if(e.code==='ArrowDown'&&!collide(px,py+1,piece)){py++;draw(0);}
    if(e.code==='ArrowUp'){var r=rotate(piece);if(!collide(px,py,r))piece=r;draw(0);}
    if(e.code==='Space'){while(!collide(px,py+1,piece))py++;lock();newPiece();draw(0);}
    if(['ArrowLeft','ArrowRight','ArrowDown','ArrowUp','Space'].includes(e.code))e.preventDefault();}
  newBoard();score=0;newPiece();
  document.addEventListener('keydown',kd);iv=setInterval(tick,500);
  el._fkCleanup=function(){clearInterval(iv);document.removeEventListener('keydown',kd);};
  lbl(el,'←→↓ move · ↑ rotate · SPACE drop');
}};

/* 2048 */
G.g2048={title:'2048',cat:'puzzle',render:function(el){
  el.innerHTML='';var d=document.createElement('div');d.style.cssText='font-family:monospace;padding:8px;';
  el.appendChild(d);var grid,score;
  function init(){grid=[[0,0,0,0],[0,0,0,0],[0,0,0,0],[0,0,0,0]];score=0;add();add();draw();}
  function add(){var empty=[];grid.forEach(function(r,ri){r.forEach(function(c,ci){if(!c)empty.push([ri,ci]);});});if(!empty.length)return;var p=empty[rnd(empty.length)];grid[p[0]][p[1]]=rnd(10)<9?2:4;}
  function move(dir){var moved=false;
    function slide(row){var f=row.filter(function(x){return x;});for(var i=0;i<f.length-1;i++){if(f[i]===f[i+1]){f[i]*=2;score+=f[i];f.splice(i+1,1);}}while(f.length<4)f.push(0);if(f.join()!==row.join())moved=true;return f;}
    if(dir===0||dir===2){grid=grid.map(function(r){return dir===0?slide(r):slide(r.reverse()).reverse();});}
    else{var t=grid[0].map(function(_,i){return grid.map(function(r){return r[i];});});t=t.map(function(r){return dir===1?slide(r):slide(r.reverse()).reverse();});grid=t[0].map(function(_,i){return t.map(function(r){return r[i];});});}
    if(moved){add();draw();}}
  var TCLR={2:'#f0ede4',4:'#ede0c8',8:'#f2b179',16:'#f59563',32:'#f67c5f',64:'#f65e3b',128:'#edcf72',256:'#edcc61',512:'#edc850',1024:'#edc53f',2048:'#edc22e'};
  function draw(){d.innerHTML='<div style="text-align:center;color:rgba(255,255,255,.5);font-size:11px;margin-bottom:6px">Score: '+score+'</div>'+
    '<div style="display:grid;grid-template-columns:repeat(4,70px);gap:6px;background:#0a1322;padding:8px;border-radius:6px;width:fit-content;margin:0 auto">'+
    grid.map(function(r){return r.map(function(c){var bg=TCLR[c]||'rgba(255,255,255,.04)';var fg=c>4?'#776e65':'rgba(255,255,255,.5)';return '<div style="width:70px;height:70px;background:'+bg+';border-radius:4px;display:flex;align-items:center;justify-content:center;font-size:'+(c>=1024?'16':'20')+'px;font-weight:bold;color:'+fg+'">'+( c||'')+'</div>';}).join('');}).join('')+'</div>';}
  var km={ArrowLeft:0,ArrowRight:2,ArrowUp:3,ArrowDown:1};
  function kd(e){if(km[e.code]!==undefined){move(km[e.code]);e.preventDefault();}}
  document.addEventListener('keydown',kd);el._fkCleanup=function(){document.removeEventListener('keydown',kd);};
  init();lbl(el,'Arrow keys to merge tiles');
}};

/* REACTION */
G.reaction={title:'Reaction',cat:'mini',render:function(el){
  el.innerHTML='';var d=document.createElement('div');d.style.cssText='text-align:center;padding:20px;font-family:monospace;';
  el.appendChild(d);var state='wait',t0,best=null,iv;
  function show(msg,clr){d.innerHTML='<div style="font-size:14px;color:rgba(255,255,255,.4);margin-bottom:16px">Reaction Test</div>'+
    '<div id="rbox" style="width:220px;height:120px;margin:0 auto;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:13px;cursor:pointer;border:1px solid rgba(255,255,255,.1);background:'+clr+';color:rgba(255,255,255,.8)">'+msg+'</div>'+
    (best?'<div style="margin-top:12px;font-size:11px;color:rgba(255,255,255,.3)">Best: '+best+'ms</div>':'');}
  function start(){state='wait';show('Click when GREEN','rgba(255,255,255,.04)');
    var delay=1000+rnd(3000);clearTimeout(iv);iv=setTimeout(function(){state='ready';t0=Date.now();show('CLICK NOW!','rgba(31,204,124,.3)');},delay);}
  d.addEventListener('click',function(){
    if(state==='wait'){clearTimeout(iv);state='early';show('Too early! Click to retry','rgba(255,80,80,.2)');}
    else if(state==='ready'){var ms=Date.now()-t0;state='done';if(!best||ms<best)best=ms;show(ms+' ms'+(ms<200?' ⚡':''),'rgba(31,204,124,.15)');}
    else start();});
  start();el._fkCleanup=function(){clearTimeout(iv);};
  lbl(el,'Click when it turns green');
}};

/* NUMBER GUESS */
G.numguess={title:'Number Guess',cat:'mini',render:function(el){
  el.innerHTML='';var d=document.createElement('div');d.style.cssText='padding:16px;font-family:monospace;';
  el.appendChild(d);var target,tries,max=100;
  function init(){target=1+rnd(max);tries=0;render('');}
  function render(msg){d.innerHTML='<div style="color:rgba(255,255,255,.5);font-size:12px;margin-bottom:12px">Guess 1–'+max+'</div>'+
    '<div style="display:flex;gap:8px;margin-bottom:12px"><input id="gi" type="number" min="1" max="'+max+'" style="background:rgba(0,0,0,.4);border:1px solid rgba(255,255,255,.15);color:#fff;padding:6px 10px;font-family:monospace;font-size:12px;border-radius:3px;width:80px" placeholder="?">'+
    '<button onclick="window._gGuess()" style="padding:6px 14px;background:rgba(31,204,124,.1);border:1px solid rgba(31,204,124,.3);color:#1FCC7C;font-family:monospace;font-size:11px;cursor:pointer;border-radius:3px">Guess</button></div>'+
    (msg?'<div style="font-size:11px;color:rgba(255,255,255,.5);margin-bottom:8px">'+msg+'</div>':'')+
    '<div style="font-size:10px;color:rgba(255,255,255,.25)">Tries: '+tries+'</div>';}
  window._gGuess=function(){var v=parseInt(document.getElementById('gi').value);if(!v)return;tries++;
    if(v===target)render('🎉 Correct in '+tries+' tries! <button onclick="window._gNew()" style="padding:3px 8px;background:rgba(31,204,124,.1);border:1px solid rgba(31,204,124,.3);color:#1FCC7C;font-family:monospace;font-size:10px;cursor:pointer;border-radius:2px">New game</button>');
    else render(v<target?'Too low ↑':'Too high ↓');};
  window._gNew=init;init();el._fkCleanup=function(){delete window._gGuess;delete window._gNew;};
}};

/* SLOTS */
G.slots={title:'Slots',cat:'casino',render:function(el){
  el.innerHTML='';var d=document.createElement('div');d.style.cssText='text-align:center;padding:16px;font-family:monospace;';
  el.appendChild(d);var SYMS=['🍒','🍋','🔔','⭐','7️⃣','💎'],coins=20,spin=false;
  function reels(){return [SYMS[rnd(6)],SYMS[rnd(6)],SYMS[rnd(6)]];}
  function win(r){if(r[0]===r[1]&&r[1]===r[2])return r[0]==='💎'?50:r[0]==='7️⃣'?20:10;if(r[0]===r[1]||r[1]===r[2])return 2;return 0;}
  var cur=['🍒','🍋','🔔'],msg='',iv2;
  function draw(){d.innerHTML='<div style="font-size:11px;color:rgba(255,255,255,.4);margin-bottom:10px">Coins: '+coins+'</div>'+
    '<div style="font-size:40px;letter-spacing:10px;background:rgba(0,0,0,.4);padding:16px 20px;border-radius:6px;border:1px solid rgba(255,255,255,.1);display:inline-block;margin-bottom:12px">'+cur.join(' ')+'</div><br>'+
    (msg?'<div style="font-size:12px;color:#1FCC7C;margin:8px 0">'+msg+'</div>':'')+
    '<button '+(spin||coins<1?'disabled':'')+' onclick="window._gSpin()" style="padding:8px 24px;background:rgba(245,166,35,.1);border:1px solid rgba(245,166,35,.3);color:#F5A623;font-family:monospace;font-size:12px;cursor:pointer;border-radius:3px;margin-top:4px">🎰 Spin (-1)</button>';}
  window._gSpin=function(){if(spin||coins<1)return;coins--;spin=true;msg='';var count=0;
    clearInterval(iv2);iv2=setInterval(function(){cur=reels();draw();count++;if(count>12){clearInterval(iv2);var w=win(cur);if(w){coins+=w;msg='Win! +'+w+' coins';}else msg='No match';spin=false;draw();}},80);};
  draw();el._fkCleanup=function(){clearInterval(iv2);delete window._gSpin;};
}};

/* WAR */
G.war={title:'War',cat:'cards',render:function(el){
  el.innerHTML='';var d=document.createElement('div');d.style.cssText='text-align:center;padding:16px;font-family:monospace;';
  el.appendChild(d);var deck,p,c,msg;
  var SUITS=['♠','♥','♦','♣'],VALS=['2','3','4','5','6','7','8','9','10','J','Q','K','A'];
  function newDeck(){var dk=[];SUITS.forEach(function(s){VALS.forEach(function(v,i){dk.push({s:s,v:v,n:i+2});});});for(var i=dk.length-1;i>0;i--){var j=rnd(i+1);var t=dk[i];dk[i]=dk[j];dk[j]=t;}return dk;}
  function init(){deck=newDeck();p=deck.slice(0,26);c=deck.slice(26);msg='Click Flip!';draw();}
  function flip(){if(!p.length||!c.length){msg=(!p.length?'CPU wins!':'You win!');draw();return;}
    var pc=p.shift(),cc=c.shift(),res=pc.n>cc.n?'You win!':pc.n<cc.n?'CPU wins!':'War!';
    if(pc.n>cc.n){p.push(pc,cc);}else if(pc.n<cc.n){c.push(pc,cc);}else{p.push(pc);c.push(cc);}
    msg='You: '+pc.v+pc.s+' vs CPU: '+cc.v+cc.s+' — '+res;draw();}
  function card(cd){return'<span style="display:inline-block;width:48px;height:66px;background:#1a2434;border:1px solid rgba(255,255,255,.15);border-radius:5px;font-size:16px;line-height:66px;color:'+(['♥','♦'].includes(cd.s)?'#FF5F5F':'rgba(255,255,255,.8)')+'">'+(cd.v+cd.s)+'</span>';}
  function draw(){d.innerHTML='<div style="font-size:11px;color:rgba(255,255,255,.3);margin-bottom:12px">You: '+p.length+' cards · CPU: '+c.length+' cards</div>'+
    '<div style="display:flex;justify-content:center;gap:20px;margin-bottom:12px">'+(p.length?card(p[0]):'<span style="display:inline-block;width:48px;height:66px;background:rgba(255,255,255,.04);border:1px dashed rgba(255,255,255,.1);border-radius:5px;line-height:66px;color:rgba(255,255,255,.2)">none</span>')+
    (c.length?card(c[0]):'<span style="display:inline-block;width:48px;height:66px;background:rgba(255,255,255,.04);border:1px dashed rgba(255,255,255,.1);border-radius:5px;line-height:66px;color:rgba(255,255,255,.2)">none</span>')+'</div>'+
    '<div style="font-size:11px;color:rgba(255,255,255,.5);margin-bottom:12px">'+msg+'</div>'+
    '<button onclick="window._gFlip()" style="padding:7px 20px;background:rgba(31,204,124,.1);border:1px solid rgba(31,204,124,.3);color:#1FCC7C;font-family:monospace;font-size:11px;cursor:pointer;border-radius:3px">'+((!p.length||!c.length)?'New Game':'Flip')+'</button>';}
  window._gFlip=function(){if(!p.length||!c.length)init();else flip();};
  init();el._fkCleanup=function(){delete window._gFlip;};
}};

/* NIM */
G.nim={title:'Nim',cat:'strategy',render:function(el){
  el.innerHTML='';var d=document.createElement('div');d.style.cssText='padding:16px;font-family:monospace;';
  el.appendChild(d);var rows,turn,msg;
  function init(){rows=[3,5,7];turn='player';msg='Take 1-3 from any row.';draw();}
  function cpuMove(){var nim=rows.reduce(function(a,b){return a^b;},0);var moved=false;
    rows.forEach(function(r,i){if(!moved){var t=r^(r^nim);if(t<r&&t>=0){rows[i]=t;moved=true;}}});
    if(!moved){for(var i=0;i<rows.length;i++){if(rows[i]>0){rows[i]=Math.max(0,rows[i]-1);break;}}}}
  function take(row,n){if(turn!=='player'||rows[row]<n)return;rows[row]-=n;
    if(rows.every(function(r){return r===0;})){msg='You took the last — CPU wins!';draw();return;}
    turn='cpu';draw();setTimeout(function(){cpuMove();if(rows.every(function(r){return r===0;})){msg='CPU took the last — You win!';turn='done';}else turn='player';draw();},600);}
  function draw(){var rowHTML=rows.map(function(r,i){
    var sticks='';for(var k=0;k<r;k++)sticks+='<span style="display:inline-block;width:8px;height:28px;background:#1FCC7C;border-radius:2px;margin:0 2px;vertical-align:middle"></span>';
    return'<div style="margin-bottom:8px;display:flex;align-items:center;gap:10px"><span style="color:rgba(255,255,255,.3);font-size:10px;width:40px">Row '+(i+1)+':</span><span>'+sticks+'</span>'+
    (turn==='player'&&r>0?[1,2,3].filter(function(n){return n<=r;}).map(function(n){return'<button onclick="window._nim('+i+','+n+')" style="padding:3px 8px;background:rgba(31,204,124,.07);border:1px solid rgba(31,204,124,.2);color:#1FCC7C;font-family:monospace;font-size:9px;cursor:pointer;border-radius:2px;margin-left:4px">-'+n+'</button>';}).join(''):'')+'</div>';}).join('');
    d.innerHTML='<div style="font-size:12px;color:rgba(255,255,255,.5);margin-bottom:12px">Nim — take the last stick to lose</div>'+
    rowHTML+'<div style="font-size:11px;color:rgba(255,255,255,.4);margin-top:8px">'+msg+'</div>'+
    (turn==='done'?'<button onclick="window._nimNew()" style="margin-top:10px;padding:6px 14px;background:rgba(31,204,124,.1);border:1px solid rgba(31,204,124,.3);color:#1FCC7C;font-family:monospace;font-size:10px;cursor:pointer;border-radius:3px">New Game</button>':'');}
  window._nim=take;window._nimNew=init;init();
  el._fkCleanup=function(){delete window._nim;delete window._nimNew;};
}};

/* REVERSI */
G.reversi={title:'Reversi',cat:'strategy',render:function(el){
  var C=cv(el,320,320),x=C.getContext('2d'),N=8,SZ=40;
  var board,turn;
  function init(){board=Array.from({length:N},function(){return new Array(N).fill(0)});board[3][3]=1;board[4][4]=1;board[3][4]=2;board[4][3]=2;turn=2;draw();}
  function flips(r,c,t){var opp=3-t,res=[];var dirs=[[-1,-1],[-1,0],[-1,1],[0,-1],[0,1],[1,-1],[1,0],[1,1]];
    dirs.forEach(function(d){var fl=[],nr=r+d[0],nc=c+d[1];while(nr>=0&&nr<N&&nc>=0&&nc<N&&board[nr][nc]===opp){fl.push([nr,nc]);nr+=d[0];nc+=d[1];}if(fl.length&&nr>=0&&nr<N&&nc>=0&&nc<N&&board[nr][nc]===t)res=res.concat(fl);});return res;}
  function valid(t){var v=[];for(var r=0;r<N;r++)for(var c=0;c<N;c++)if(!board[r][c]&&flips(r,c,t).length)v.push([r,c]);return v;}
  function place(r,c){var fl=flips(r,c,turn);if(!fl.length)return;board[r][c]=turn;fl.forEach(function(p){board[p[0]][p[1]]=turn;});turn=3-turn;if(!valid(turn).length)turn=3-turn;draw();}
  function cpuMove(){var v=valid(1);if(!v.length)return;var best=v.reduce(function(a,b){return flips(b[0],b[1],1).length>flips(a[0],a[1],1).length?b:a;},v[0]);place(best[0],best[1]);}
  function count(t){return board.reduce(function(s,r){return s+r.filter(function(c){return c===t;}).length;},0);}
  function draw(){x.fillStyle='#15552a';x.fillRect(0,0,320,320);
    for(var r=0;r<N;r++)for(var c=0;c<N;c++){x.strokeStyle='rgba(0,0,0,.3)';x.strokeRect(c*SZ,r*SZ,SZ,SZ);
      if(board[r][c]){x.fillStyle=board[r][c]===1?'#111':'#eee';x.beginPath();x.arc(c*SZ+SZ/2,r*SZ+SZ/2,16,0,6.28);x.fill();}}
    var v=valid(turn);v.forEach(function(p){x.strokeStyle='rgba(255,255,255,.25)';x.beginPath();x.arc(p[1]*SZ+SZ/2,p[0]*SZ+SZ/2,8,0,6.28);x.stroke();});
    x.fillStyle='rgba(0,0,0,.7)';x.fillRect(0,300,320,20);x.fillStyle='rgba(255,255,255,.5)';x.font='10px monospace';x.fillText('⬛'+count(1)+' ⬜'+count(2)+(turn===2?' — Your turn':' — CPU thinking'),4,314);}
  C.addEventListener('click',function(e){if(turn!==2)return;var r=Math.floor(e.offsetY/SZ),c=Math.floor(e.offsetX/SZ);if(flips(r,c,2).length){place(r,c);setTimeout(function(){if(turn===1)cpuMove();},400);}});
  init();el._fkCleanup=function(){};lbl(el,'You are White (⬜) · Click to place');
}};

/* MAZE */
G.maze={title:'Maze',cat:'puzzleplus',render:function(el){
  var C=cv(el,360,360),x=C.getContext('2d'),COLS=15,ROWS=15,SZ=24;
  var walls,px,py,time0,iv2;
  function init(){
    walls=Array.from({length:ROWS},function(){return Array.from({length:COLS},function(){return{r:true,b:true};});});
    var vis=Array.from({length:ROWS},function(){return new Array(COLS).fill(false);}),stack=[[0,0]];vis[0][0]=true;
    while(stack.length){var cur=stack[stack.length-1],cr=cur[0],cc=cur[1];
      var nb=[[cr-1,cc,'r',-1,0],[cr+1,cc,'r',1,0],[cr,cc-1,'b',0,-1],[cr,cc+1,'b',0,1]].filter(function(n){return n[0]>=0&&n[0]<ROWS&&n[1]>=0&&n[1]<COLS&&!vis[n[0]][n[1]];});
      if(!nb.length){stack.pop();}else{var n=nb[rnd(nb.length)];vis[n[0]][n[1]]=true;
        if(n[2]==='r'){if(n[3]>0)walls[cr][cc].b=false;else walls[n[0]][n[1]].b=false;}
        else{if(n[4]>0)walls[cr][cc].r=false;else walls[n[0]][n[1]].r=false;}
        stack.push([n[0],n[1]]);}}
    px=0;py=0;time0=Date.now();}
  function draw(){x.fillStyle='#050a10';x.fillRect(0,0,360,360);
    x.strokeStyle='rgba(31,204,124,.4)';x.lineWidth=1;
    for(var r=0;r<ROWS;r++)for(var c=0;c<COLS;c++){var wx=c*SZ,wy=r*SZ;
      if(walls[r][c].r){x.beginPath();x.moveTo(wx,wy+SZ);x.lineTo(wx+SZ,wy+SZ);x.stroke();}
      if(walls[r][c].b){x.beginPath();x.moveTo(wx+SZ,wy);x.lineTo(wx+SZ,wy+SZ);x.stroke();}}
    x.strokeStyle='rgba(31,204,124,.4)';x.strokeRect(0,0,COLS*SZ,ROWS*SZ);
    x.fillStyle='#1FCC7C';x.fillRect((COLS-1)*SZ+8,(ROWS-1)*SZ+8,SZ-16,SZ-16);
    x.fillStyle='#F5A623';x.beginPath();x.arc(px*SZ+SZ/2,py*SZ+SZ/2,8,0,6.28);x.fill();}
  function canMove(r,c,dr,dc){if(dc===1)return!walls[r][c].b;if(dc===-1)return c>0&&!walls[r][c-1].b;if(dr===1)return!walls[r][c].r;if(dr===-1)return r>0&&!walls[r-1][c].r;return false;}
  function kd(e){var nr=py,nc=px;if(e.code==='ArrowUp')nr--;else if(e.code==='ArrowDown')nr++;else if(e.code==='ArrowLeft')nc--;else if(e.code==='ArrowRight')nc++;else return;
    e.preventDefault();if(nr<0||nr>=ROWS||nc<0||nc>=COLS)return;if(canMove(py,px,nr-py,nc-px)){py=nr;px=nc;}draw();
    if(px===COLS-1&&py===ROWS-1){var t=Math.round((Date.now()-time0)/1000);x.fillStyle='rgba(0,0,0,.85)';x.fillRect(50,130,260,70);x.fillStyle='#1FCC7C';x.font='bold 14px monospace';x.textAlign='center';x.fillText('SOLVED! '+t+'s',180,165);x.textAlign='left';}}
  document.addEventListener('keydown',kd);init();draw();
  el._fkCleanup=function(){document.removeEventListener('keydown',kd);};lbl(el,'Arrow keys · reach the green square');
}};

/* RUNNER */
G.runner={title:'Runner',cat:'action',render:function(el){
  var C=cv(el,400,200),x=C.getContext('2d'),W=400,H=200;
  var py,vy,grav=0.6,obs=[],sc,speed,iv,state;
  function init(){py=H-40;vy=0;obs=[];sc=0;speed=3;state=1;clearInterval(iv);iv=setInterval(tick,16);}
  function tick(){vy+=grav;py+=vy;if(py>=H-30){py=H-30;vy=0;}
    speed=3+sc/200;obs.forEach(function(o){o.x-=speed;});
    if(!obs.length||obs[obs.length-1].x<W-120-rnd(80))obs.push({x:W,w:16,h:20+rnd(30)});
    obs=obs.filter(function(o){return o.x>-30;});
    obs.forEach(function(o){if(50<o.x+o.w&&34>o.x&&py+30>H-o.h&&py<H){state=0;clearInterval(iv);}});
    sc++;draw();}
  function draw(){x.fillStyle='#050a10';x.fillRect(0,0,W,H);
    x.fillStyle='rgba(31,204,124,.2)';x.fillRect(0,H-5,W,5);
    x.fillStyle='#1FCC7C';x.fillRect(34,py,22,30);
    obs.forEach(function(o){x.fillStyle='#FF5F5F';x.fillRect(o.x,H-o.h,o.w,o.h);});
    x.fillStyle='rgba(255,255,255,.4)';x.font='10px monospace';x.fillText('Score:'+Math.floor(sc/10),4,15);
    if(!state){x.fillStyle='rgba(0,0,0,.8)';x.fillRect(100,70,200,60);x.fillStyle='#FF5F5F';x.font='bold 13px monospace';x.textAlign='center';x.fillText('GAME OVER',W/2,98);x.fillStyle='rgba(255,255,255,.5)';x.font='10px monospace';x.fillText('SPACE to retry',W/2,116);x.textAlign='left';}}
  function kd(e){if(e.code==='Space'){e.preventDefault();if(!state)init();else if(py>=H-32)vy=-12;}}
  document.addEventListener('keydown',kd);C.addEventListener('click',function(){if(!state)init();else if(py>=H-32)vy=-12;});
  init();el._fkCleanup=function(){clearInterval(iv);document.removeEventListener('keydown',kd);};
  lbl(el,'SPACE or tap to jump');
}};

/* DODGE */
G.dodge={title:'Dodge',cat:'action',render:function(el){
  var C=cv(el,360,320),x=C.getContext('2d'),W=360,H=320;
  var px,balls,sc,iv,state,mouse;
  mouse={x:W/2,y:H-40};
  function init(){px=W/2;balls=[];sc=0;state=1;clearInterval(iv);iv=setInterval(tick,16);}
  function tick(){sc++;if(sc%40===0)balls.push({x:rnd(W-20)+10,y:-10,vy:1.5+sc/800,vx:(rnd(3)-1)*0.5});
    balls.forEach(function(b){b.y+=b.vy;b.x+=b.vx;if(b.x<5||b.x>W-5)b.vx*=-1;});
    balls=balls.filter(function(b){return b.y<H+20;});
    balls.forEach(function(b){if(Math.abs(b.x-px)<14&&Math.abs(b.y-(H-30))<14){state=0;clearInterval(iv);}});
    draw();}
  function draw(){x.fillStyle='#050a10';x.fillRect(0,0,W,H);
    x.fillStyle='#1FCC7C';x.fillRect(px-10,H-40,20,20);
    balls.forEach(function(b){x.fillStyle='#FF5F5F';x.beginPath();x.arc(b.x,b.y,8,0,6.28);x.fill();});
    x.fillStyle='rgba(255,255,255,.4)';x.font='10px monospace';x.fillText('Score:'+Math.floor(sc/60),4,15);
    if(!state){x.fillStyle='rgba(0,0,0,.8)';x.fillRect(80,120,200,60);x.fillStyle='#FF5F5F';x.font='bold 13px monospace';x.textAlign='center';x.fillText('HIT!',W/2,148);x.fillStyle='rgba(255,255,255,.5)';x.font='10px monospace';x.fillText('Click to retry',W/2,168);x.textAlign='left';}}
  C.addEventListener('mousemove',function(e){var r=C.getBoundingClientRect();px=clamp(e.clientX-r.left,10,W-10);});
  C.addEventListener('click',function(){if(!state)init();});
  function clamp(v,a,b){return Math.max(a,Math.min(b,v));}
  init();el._fkCleanup=function(){clearInterval(iv);};lbl(el,'Move mouse to dodge · click restart');
}};

/* TRIVIA */
G.trivia={title:'Trivia',cat:'action',render:function(el){
  el.innerHTML='';var d=document.createElement('div');d.style.cssText='padding:12px;font-family:monospace;';el.appendChild(d);
  var Qs=[
    {q:'What does HTTP stand for?',a:['HyperText Transfer Protocol','High Transfer Text Protocol','Hyper Terminal Transfer Protocol','Home Text Transfer Protocol'],c:0},
    {q:'Which port does SSH use by default?',a:['22','80','443','21'],c:0},
    {q:'What is the loopback IP address?',a:['127.0.0.1','192.168.0.1','10.0.0.1','0.0.0.0'],c:0},
    {q:'What does BLE stand for?',a:['Bluetooth Low Energy','Basic Link Encryption','Binary Layer Exchange','Broadband LAN Extension'],c:0},
    {q:'Which protocol does DNS use most?',a:['UDP','TCP','ICMP','ARP'],c:0},
    {q:'What frequency does 802.11ac use?',a:['5 GHz','2.4 GHz','900 MHz','60 GHz'],c:0},
    {q:'What does RFID stand for?',a:['Radio-Frequency IDentification','Random Frequency ID','RF Interface Device','Radio Field Induction Detector'],c:0},
    {q:'What is a MAC address length?',a:['48 bits','32 bits','64 bits','128 bits'],c:0},
    {q:'Which layer is IP on?',a:['Network (3)','Transport (4)','Data Link (2)','Application (7)'],c:0},
    {q:'What does ARP do?',a:['Maps IP to MAC','Maps MAC to IP','Routes packets','Encrypts data'],c:0}
  ];
  var qi=0,sc=0,answered=false;
  function shuffle(a){for(var i=a.length-1;i>0;i--){var j=rnd(i+1);var t=a[i];a[i]=a[j];a[j]=t;}return a;}
  Qs=shuffle(Qs);
  function draw(sel){var q=Qs[qi];d.innerHTML='<div style="font-size:10px;color:rgba(255,255,255,.3);margin-bottom:8px">Q '+(qi+1)+'/'+Qs.length+' · Score: '+sc+'</div>'+
    '<div style="font-size:12px;color:rgba(255,255,255,.75);margin-bottom:12px;line-height:1.5">'+q.q+'</div>'+
    q.a.map(function(a,i){var col=sel===undefined?'rgba(255,255,255,.08)':i===q.c?'rgba(31,204,124,.2)':i===sel?'rgba(255,80,80,.2)':'rgba(255,255,255,.04)';
      var border=sel===undefined?'rgba(255,255,255,.12)':i===q.c?'rgba(31,204,124,.4)':i===sel?'rgba(255,80,80,.35)':'rgba(255,255,255,.06)';
      return'<div onclick="window._qa('+i+')" style="padding:8px 10px;margin-bottom:6px;background:'+col+';border:1px solid '+border+';border-radius:4px;font-size:11px;cursor:pointer;line-height:1.4">'+a+'</div>';}).join('');}
  window._qa=function(i){if(answered)return;answered=true;if(i===Qs[qi].c)sc++;draw(i);
    setTimeout(function(){qi++;if(qi>=Qs.length){d.innerHTML='<div style="text-align:center;padding:20px"><div style="font-size:14px;color:#1FCC7C;margin-bottom:8px">Done! Score: '+sc+'/'+Qs.length+'</div><button onclick="window._qNew()" style="padding:7px 18px;background:rgba(31,204,124,.1);border:1px solid rgba(31,204,124,.3);color:#1FCC7C;font-family:monospace;font-size:11px;cursor:pointer;border-radius:3px">Play Again</button></div>';}else{answered=false;draw();}},1200);};
  window._qNew=function(){qi=0;sc=0;answered=false;Qs=shuffle(Qs);draw();};
  draw();el._fkCleanup=function(){delete window._qa;delete window._qNew;};
}};

/* PIXEL ART */
G.pixelart={title:'Pixel Art',cat:'creative',render:function(el){
  var C=cv(el,320,320),x=C.getContext('2d'),N=16,SZ=20;
  var grid=Array.from({length:N},function(){return new Array(N).fill('#050a10');}),clr='#1FCC7C',drawing=false;
  var PALETTE=['#1FCC7C','#FF5F5F','#F5A623','#4FC3F7','#CE93D8','#fff','#F9E04B','#FF8A65','#4DB6AC','#050a10'];
  function draw(){x.fillStyle='#050a10';x.fillRect(0,0,320,320);
    for(var r=0;r<N;r++)for(var c=0;c<N;c++){x.fillStyle=grid[r][c];x.fillRect(c*SZ,r*SZ,SZ,SZ);x.strokeStyle='rgba(255,255,255,.04)';x.strokeRect(c*SZ,r*SZ,SZ,SZ);}
    PALETTE.forEach(function(p,i){x.fillStyle=p;x.fillRect(i*(N+2),N*SZ+2,N,N);if(p===clr){x.strokeStyle='#fff';x.lineWidth=2;x.strokeRect(i*(N+2),N*SZ+2,N,N);x.lineWidth=1;}});
    x.fillStyle='rgba(255,255,255,.2)';x.font='9px monospace';x.fillText('▶ '+clr,PALETTE.length*(N+2)+4,N*SZ+12);}
  function paint(e){var r=C.getBoundingClientRect(),mx=e.clientX-r.left,my=e.clientY-r.top;
    if(my>N*SZ){var pi=Math.floor(mx/(N+2));if(pi>=0&&pi<PALETTE.length){clr=PALETTE[pi];draw();}return;}
    var gr=Math.floor(my/SZ),gc=Math.floor(mx/SZ);if(gr>=0&&gr<N&&gc>=0&&gc<N){grid[gr][gc]=clr;draw();}}
  C.addEventListener('mousedown',function(e){drawing=true;paint(e);});
  C.addEventListener('mousemove',function(e){if(drawing)paint(e);});
  C.addEventListener('mouseup',function(){drawing=false;});
  draw();el._fkCleanup=function(){};lbl(el,'Click palette to pick colour · draw on grid');
}};

/* GRAVITY */
G.gravity={title:'Gravity',cat:'creative',render:function(el){
  var C=cv(el,360,320),x=C.getContext('2d'),W=360,H=320;
  var balls=[],iv;
  for(var i=0;i<8;i++)balls.push({x:rnd(W-40)+20,y:rnd(H/2),vx:(rnd(3)-1),vy:0,r:8+rnd(10),c:['#1FCC7C','#FF5F5F','#F5A623','#4FC3F7'][rnd(4)]});
  function tick(){balls.forEach(function(b){b.vy+=0.3;b.x+=b.vx;b.y+=b.vy;
    if(b.x<b.r){b.x=b.r;b.vx=Math.abs(b.vx)*0.85;}if(b.x>W-b.r){b.x=W-b.r;b.vx=-Math.abs(b.vx)*0.85;}
    if(b.y>H-b.r){b.y=H-b.r;b.vy=-Math.abs(b.vy)*0.75;b.vx*=0.98;}if(b.y<b.r){b.y=b.r;b.vy=Math.abs(b.vy);}});
    for(var i=0;i<balls.length;i++)for(var j=i+1;j<balls.length;j++){
      var a=balls[i],bj=balls[j],dx=bj.x-a.x,dy=bj.y-a.y,dist=Math.sqrt(dx*dx+dy*dy);
      if(dist<a.r+bj.r&&dist>0){var nx=dx/dist,ny=dy/dist,p=2*((a.vx-bj.vx)*nx+(a.vy-bj.vy)*ny)/(2);
        a.vx-=p*nx;a.vy-=p*ny;bj.vx+=p*nx;bj.vy+=p*ny;var overlap=(a.r+bj.r-dist)/2;a.x-=overlap*nx;a.y-=overlap*ny;bj.x+=overlap*nx;bj.y+=overlap*ny;}}
    draw();}
  function draw(){x.fillStyle='#050a10';x.fillRect(0,0,W,H);
    balls.forEach(function(b){x.fillStyle=b.c;x.beginPath();x.arc(b.x,b.y,b.r,0,6.28);x.fill();});}
  C.addEventListener('click',function(e){var r=C.getBoundingClientRect();balls.push({x:e.clientX-r.left,y:e.clientY-r.top,vx:(rnd(5)-2),vy:-5,r:8+rnd(14),c:['#1FCC7C','#FF5F5F','#F5A623','#4FC3F7','#CE93D8'][rnd(5)]});});
  iv=setInterval(tick,16);el._fkCleanup=function(){clearInterval(iv);};lbl(el,'Click to add balls');
}};

/* PIPE */
G.pipe={title:'Pipe',cat:'puzzleplus',render:function(el){
  el.innerHTML='';var d=document.createElement('div');d.style.cssText='padding:8px;font-family:monospace;';el.appendChild(d);
  var N=6,grid,solved;
  var TYPES=['─','│','┌','┐','└','┘','┼'];
  var CONN={
    '─':{l:1,r:1,u:0,d:0},'│':{l:0,r:0,u:1,d:1},
    '┌':{l:0,r:1,u:0,d:1},'┐':{l:1,r:0,u:0,d:1},
    '└':{l:0,r:1,u:1,d:0},'┘':{l:1,r:0,u:1,d:0},'┼':{l:1,r:1,u:1,d:1}
  };
  function init(){grid=Array.from({length:N},function(){return Array.from({length:N},function(){return{t:TYPES[rnd(7)],r:rnd(4)};});});solved=false;draw();}
  function rotate(cell){cell.r=(cell.r+1)%4;}
  function getConn(cell){var t=TYPES[TYPES.indexOf(cell.t)],r=cell.r,c=CONN[t]||{l:0,r:0,u:0,d:0};
    for(var i=0;i<r;i++){c={l:c.d,r:c.u,u:c.l,d:c.r};}return c;}
  function check(){var ok=true;for(var r=0;r<N;r++)for(var c=0;c<N;c++){var cc=getConn(grid[r][c]);
    if(c<N-1&&cc.r!==getConn(grid[r][c+1]).l)ok=false;if(r<N-1&&cc.d!==getConn(grid[r+1][c]).u)ok=false;}return ok;}
  function draw(){d.innerHTML='<div style="display:grid;grid-template-columns:repeat('+N+',40px);gap:2px;margin-bottom:8px">'+
    grid.map(function(row,ri){return row.map(function(cell,ci){var c=getConn(cell);var col=c.l&&c.r&&c.u&&c.d?'#1FCC7C':c.l||c.r||c.u||c.d?'#4FC3F7':'rgba(255,255,255,.2)';
      return'<div onclick="window._pipe('+ri+','+ci+')" style="width:40px;height:40px;background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);border-radius:3px;display:flex;align-items:center;justify-content:center;font-size:20px;color:'+col+';cursor:pointer;transform:rotate('+cell.r*90+'deg)">'+cell.t+'</div>';}).join('');}).join('')+'</div>'+
    (solved?'<div style="color:#1FCC7C;font-size:11px">✓ All pipes connected!</div>':'<div style="font-size:10px;color:rgba(255,255,255,.3)">Click tiles to rotate · connect all pipes</div>')+
    '<div style="margin-top:8px"><button onclick="window._pipeNew()" style="padding:5px 12px;background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.1);color:rgba(255,255,255,.4);font-family:monospace;font-size:10px;cursor:pointer;border-radius:3px">New Puzzle</button></div>';}
  window._pipe=function(r,c){rotate(grid[r][c]);if(check())solved=true;draw();};
  window._pipeNew=init;init();el._fkCleanup=function(){delete window._pipe;delete window._pipeNew;};
}};

/* CHAIN REACTION */
G.chain={title:'Chain',cat:'puzzleplus',render:function(el){
  var C=cv(el,360,320),x=C.getContext('2d'),W=360,H=320;
  var atoms,explosions,turn,scores,iv;
  function init(){atoms=[];explosions=[];turn=1;scores={1:0,2:0};
    for(var i=0;i<6;i++)atoms.push({x:60+rnd(240),y:40+rnd(240),owner:1+rnd(2),mass:1,vx:0,vy:0});}
  function explode(a){var idx=atoms.indexOf(a);if(idx<0)return;atoms.splice(idx,1);
    for(var i=0;i<4;i++){var ang=i*Math.PI/2,speed=4+rnd(2);explosions.push({x:a.x,y:a.y,vx:Math.cos(ang)*speed,vy:Math.sin(ang)*speed,owner:a.owner,life:40});}}
  function tick(){explosions.forEach(function(e){e.x+=e.vx;e.y+=e.vy;e.life--;});
    explosions=explosions.filter(function(e){return e.life>0&&e.x>0&&e.x<W&&e.y>0&&e.y<H;});
    explosions.forEach(function(exp){atoms.forEach(function(a){var dx=a.x-exp.x,dy=a.y-exp.y;if(Math.sqrt(dx*dx+dy*dy)<20&&a.owner!==exp.owner){a.owner=exp.owner;a.mass++;if(a.mass>3)explode(a);}});});
    if(!explosions.length){clearInterval(iv);iv=null;}draw();}
  function draw(){x.fillStyle='#050a10';x.fillRect(0,0,W,H);
    atoms.forEach(function(a){x.fillStyle=a.owner===1?'#1FCC7C':'#FF5F5F';x.beginPath();x.arc(a.x,a.y,8+a.mass*3,0,6.28);x.fill();x.fillStyle='rgba(0,0,0,.5)';x.font='9px monospace';x.textAlign='center';x.fillText(a.mass,a.x,a.y+3);x.textAlign='left';});
    explosions.forEach(function(e){x.fillStyle=(e.owner===1?'rgba(31,204,124,':'rgba(255,80,80,')+e.life/40+')';x.beginPath();x.arc(e.x,e.y,5,0,6.28);x.fill();});
    x.fillStyle='rgba(255,255,255,.4)';x.font='10px monospace';x.fillText('🟢 '+scores[1]+' · 🔴 '+scores[2]+' · Turn: '+(turn===1?'🟢':'🔴'),4,15);}
  C.addEventListener('click',function(e){if(iv)return;var r=C.getBoundingClientRect(),mx=e.clientX-r.left,my=e.clientY-r.top;
    atoms.push({x:mx,y:my,owner:turn,mass:2,vx:0,vy:0});scores[turn]++;turn=3-turn;
    clearInterval(iv);iv=setInterval(tick,30);});
  init();draw();el._fkCleanup=function(){clearInterval(iv);};lbl(el,'Click to place atom · chain reactions spread');
}};

/* CHECKERS */
G.checkers={title:'Checkers',cat:'strategy',render:function(el){
  var C=cv(el,320,320),x=C.getContext('2d'),N=8,SZ=40;
  var board,sel,turn;
  function init(){board=Array.from({length:N},function(_, r){return Array.from({length:N},function(_,c){
    if((r+c)%2===1&&r<3)return{p:2,k:false};if((r+c)%2===1&&r>4)return{p:1,k:false};return null;});});sel=null;turn=1;}
  function moves(r,c){var p=board[r][c];if(!p)return[];var dirs=[];if(p.p===1||p.k)dirs.push([-1,-1],[-1,1]);if(p.p===2||p.k)dirs.push([1,-1],[1,1]);
    var mv=[];dirs.forEach(function(d){var nr=r+d[0],nc=c+d[1];if(nr>=0&&nr<N&&nc>=0&&nc<N&&!board[nr][nc])mv.push([nr,nc]);
      var jr=r+d[0]*2,jc=c+d[1]*2;if(jr>=0&&jr<N&&jc>=0&&jc<N&&board[r+d[0]][c+d[1]]&&board[r+d[0]][c+d[1]].p!==p.p&&!board[jr][jc])mv.push([jr,jc,'jump',r+d[0],c+d[1]]);});return mv;}
  function cpuMove(){var pieces=[];for(var r=0;r<N;r++)for(var c=0;c<N;c++)if(board[r][c]&&board[r][c].p===2)pieces.push([r,c]);
    var jumps=[],normals=[];pieces.forEach(function(p){moves(p[0],p[1]).forEach(function(m){if(m[2]==='jump')jumps.push([p[0],p[1],m]);else normals.push([p[0],p[1],m]);});});
    var pick=jumps.length?jumps[rnd(jumps.length)]:normals.length?normals[rnd(normals.length)]:null;
    if(pick)doMove(pick[0],pick[1],pick[2]);turn=1;draw();}
  function doMove(fr,fc,mv){var p=board[fr][fc];board[mv[0]][mv[1]]=p;board[fr][fc]=null;if(mv[2]==='jump')board[mv[3]][mv[4]]=null;if((p.p===1&&mv[0]===0)||(p.p===2&&mv[0]===N-1))p.k=true;}
  function draw(){x.fillStyle='#050a10';x.fillRect(0,0,320,320);
    for(var r=0;r<N;r++)for(var c=0;c<N;c++){x.fillStyle=(r+c)%2===0?'#1a2434':'#0a1322';x.fillRect(c*SZ,r*SZ,SZ,SZ);
      var p=board[r][c];if(p){x.fillStyle=p.p===1?'#1FCC7C':'#FF5F5F';x.beginPath();x.arc(c*SZ+SZ/2,r*SZ+SZ/2,14,0,6.28);x.fill();if(p.k){x.fillStyle='rgba(255,255,255,.5)';x.font='bold 11px monospace';x.textAlign='center';x.fillText('K',c*SZ+SZ/2,r*SZ+SZ/2+4);x.textAlign='left';}}
      if(sel&&sel[0]===r&&sel[1]===c){x.strokeStyle='#F5A623';x.lineWidth=2;x.strokeRect(c*SZ+1,r*SZ+1,SZ-2,SZ-2);x.lineWidth=1;}};
    if(sel){moves(sel[0],sel[1]).forEach(function(m){x.fillStyle='rgba(245,166,35,.3)';x.fillRect(m[1]*SZ,m[0]*SZ,SZ,SZ);});}}
  C.addEventListener('click',function(e){if(turn!==1)return;var r=Math.floor(e.offsetY/SZ),c=Math.floor(e.offsetX/SZ);
    if(sel){var mv=moves(sel[0],sel[1]).find(function(m){return m[0]===r&&m[1]===c;});if(mv){doMove(sel[0],sel[1],mv);sel=null;turn=2;draw();setTimeout(cpuMove,400);return;}}
    sel=board[r][c]&&board[r][c].p===1?[r,c]:null;draw();});
  init();draw();el._fkCleanup=function(){};lbl(el,'You are Green · click to select+move');
}};

/* BOWLING */
G.bowling={title:'Bowling',cat:'casino',render:function(el){
  el.innerHTML='';var d=document.createElement('div');d.style.cssText='text-align:center;padding:16px;font-family:monospace;';el.appendChild(d);
  var pins,power,angle,state,frame,rolls,score;
  function init(){pins=new Array(10).fill(true);power=0;angle=0;state='aim';frame=1;rolls=0;score=0;draw();}
  function throwBall(){var hit=0;pins=pins.map(function(p){if(!p)return false;var r=Math.random()*100;return r>power*(0.5+Math.random()*0.5);});hit=pins.filter(function(p){return!p;}).length;score+=hit;rolls++;if(rolls>=2||(rolls===1&&hit===10)){frame++;rolls=0;if(frame>5){state='done';}else{pins=new Array(10).fill(true);}}state='aim';draw();}
  function draw(){var PIN_POS=[[4],[3,5],[2,4,6],[1,3,5,7],[0,2,4,6,8]];
    var pinHTML=PIN_POS.map(function(row){return'<div style="display:flex;justify-content:center;gap:4px;margin-bottom:3px">'+row.map(function(i){return'<div style="width:14px;height:14px;border-radius:50%;background:'+(pins[i]?'rgba(255,255,255,.75)':'rgba(255,255,255,.12)')+';border:1px solid rgba(255,255,255,.2)"></div>';}).join('')+'</div>';}).join('');
    d.innerHTML='<div style="font-size:11px;color:rgba(255,255,255,.4);margin-bottom:12px">Frame '+frame+'/5 · Score: '+score+'</div>'+
    '<div style="margin-bottom:12px">'+pinHTML+'</div>'+
    (state==='aim'?'<div style="font-size:11px;color:rgba(255,255,255,.4);margin-bottom:8px">Power: '+Math.round(power)+'%</div>'+
    '<input type="range" min="0" max="100" value="'+power+'" oninput="this.nextElementSibling.textContent=this.value;window._bPow=parseInt(this.value)" style="width:200px;accent-color:#1FCC7C"><span style="font-size:10px;color:rgba(255,255,255,.3);margin-left:8px">'+power+'</span><br><br>'+
    '<button onclick="window._bThrow()" style="padding:8px 24px;background:rgba(31,204,124,.1);border:1px solid rgba(31,204,124,.3);color:#1FCC7C;font-family:monospace;font-size:11px;cursor:pointer;border-radius:3px">🎳 Throw</button>'
    :state==='done'?'<div style="font-size:14px;color:#1FCC7C;margin-bottom:10px">Final: '+score+' pins</div>'+
    '<button onclick="window._bNew()" style="padding:7px 18px;background:rgba(31,204,124,.1);border:1px solid rgba(31,204,124,.3);color:#1FCC7C;font-family:monospace;font-size:11px;cursor:pointer;border-radius:3px">New Game</button>'
    :'Calculating...');}
  window._bPow=50;power=50;
  window._bThrow=function(){power=window._bPow||50;state='throwing';draw();setTimeout(throwBall,500);};
  window._bNew=init;init();el._fkCleanup=function(){delete window._bThrow;delete window._bNew;};
}};

/* BUBBLE SHOOTER */
G.bubble={title:'Bubble Shooter',cat:'casino',render:function(el){
  var C=cv(el,300,360),x=C.getContext('2d'),W=300,H=360;
  var COLS=['#FF5F5F','#1FCC7C','#F5A623','#4FC3F7','#CE93D8'];
  var grid,bx,by,bc,angle,iv;
  var R=16,COLS2=9,ROWS2=8;
  function init(){grid=Array.from({length:ROWS2},function(){return Array.from({length:COLS2},function(){return rnd(5);});});bx=W/2;by=H-20;bc=rnd(5);angle=-Math.PI/2;}
  var bullet=null;
  function fire(){if(bullet)return;bullet={x:bx,y:by,c:bc,vx:Math.cos(angle)*5,vy:Math.sin(angle)*5};bc=rnd(5);}
  function tick(){if(!bullet)return;bullet.x+=bullet.vx;bullet.y+=bullet.vy;
    if(bullet.x<R||bullet.x>W-R)bullet.vx*=-1;if(bullet.y<R){var gr=0,gc=Math.round(bullet.x/R/2);gc=Math.max(0,Math.min(COLS2-1,gc));if(grid[gr])grid[gr][gc]=bullet.c;bullet=null;pop();return;}
    var hit=false;for(var r=0;r<ROWS2&&!hit;r++)for(var c=0;c<COLS2&&!hit;c++){if(grid[r][c]===-1)continue;var gx=c*R*2+R+(r%2?R:0),gy=r*R*1.7+R;var dx=bullet.x-gx,dy=bullet.y-gy;if(Math.sqrt(dx*dx+dy*dy)<R*1.5){grid[r][c+1]===undefined?grid[r][Math.max(0,c-1)]=bullet.c:grid[r][c+1]=bullet.c;bullet=null;pop();hit=true;}}draw();}
  function pop(){var changed=true;while(changed){changed=false;for(var r=0;r<ROWS2;r++)for(var c=0;c<COLS2;c++){if(grid[r][c]===-1)continue;var nc=0;if(r>0&&grid[r-1][c]===grid[r][c])nc++;if(r<ROWS2-1&&grid[r+1][c]===grid[r][c])nc++;if(c>0&&grid[r][c-1]===grid[r][c])nc++;if(c<COLS2-1&&grid[r][c+1]===grid[r][c])nc++;if(nc>=2){grid[r][c]=-1;changed=true;}}}draw();}
  function draw(){x.fillStyle='#050a10';x.fillRect(0,0,W,H);
    for(var r=0;r<ROWS2;r++)for(var c=0;c<COLS2;c++){if(grid[r][c]===-1)continue;var gx=c*R*2+R+(r%2?R:0),gy=r*R*1.7+R;x.fillStyle=COLS[grid[r][c]];x.beginPath();x.arc(gx,gy,R-1,0,6.28);x.fill();}
    if(bullet){x.fillStyle=COLS[bullet.c];x.beginPath();x.arc(bullet.x,bullet.y,R-1,0,6.28);x.fill();}
    x.fillStyle=COLS[bc];x.beginPath();x.arc(bx,by,R-1,0,6.28);x.fill();
    x.strokeStyle='rgba(255,255,255,.15)';x.beginPath();x.moveTo(bx,by);x.lineTo(bx+Math.cos(angle)*60,by+Math.sin(angle)*60);x.stroke();}
  C.addEventListener('mousemove',function(e){var r=C.getBoundingClientRect(),mx=e.clientX-r.left,my=e.clientY-r.top;angle=Math.atan2(my-by,mx-bx);if(angle>-0.1)angle=-0.1;if(angle<-Math.PI+0.1)angle=-Math.PI+0.1;draw();});
  C.addEventListener('click',function(){fire();});
  init();iv=setInterval(tick,16);el._fkCleanup=function(){clearInterval(iv);};lbl(el,'Move mouse to aim · click to shoot');
}};

/* POKER */
G.poker={title:'Poker',cat:'cards',render:function(el){
  el.innerHTML='';var d=document.createElement('div');d.style.cssText='padding:12px;font-family:monospace;';el.appendChild(d);
  var SUITS=['♠','♥','♦','♣'],VALS=['2','3','4','5','6','7','8','9','10','J','Q','K','A'];
  var deck,hand,held,chips,state;
  function newDeck(){var dk=[];SUITS.forEach(function(s){VALS.forEach(function(v,i){dk.push({s:s,v:v,n:i+2});});});for(var i=dk.length-1;i>0;i--){var j=rnd(i+1);var t=dk[i];dk[i]=dk[j];dk[j]=t;}return dk;}
  function init(){deck=newDeck();hand=deck.splice(0,5);held=new Array(5).fill(false);chips=100;state='hold';draw();}
  function handScore(){var ns=hand.map(function(c){return c.n;}).sort(function(a,b){return a-b;});var ss=hand.map(function(c){return c.s;});var flush=ss.every(function(s){return s===ss[0];});var straight=ns.every(function(n,i){return i===0||n===ns[i-1]+1;});var counts={};ns.forEach(function(n){counts[n]=(counts[n]||0)+1;});var cv=Object.values(counts).sort(function(a,b){return b-a;});
    if(flush&&straight)return[8,'Straight Flush!',30];if(cv[0]===4)return[7,'Four of a Kind!',20];if(cv[0]===3&&cv[1]===2)return[6,'Full House!',12];if(flush)return[5,'Flush!',8];if(straight)return[4,'Straight!',6];if(cv[0]===3)return[3,'Three of a Kind!',4];if(cv[0]===2&&cv[1]===2)return[2,'Two Pair!',2];if(cv[0]===2)return[1,'Pair!',1];return[0,'High Card',0];}
  function card(c,i){var red=['♥','♦'].includes(c.s);return'<div onclick="window._hld('+i+')" style="display:inline-flex;flex-direction:column;align-items:center;justify-content:center;width:46px;height:66px;background:'+(held[i]?'rgba(31,204,124,.2)':'#1a2434')+';border:1px solid '+(held[i]?'rgba(31,204,124,.5)':'rgba(255,255,255,.12)')+';border-radius:5px;font-size:14px;cursor:pointer;color:'+(red?'#FF5F5F':'rgba(255,255,255,.85)')+'"><span>'+c.v+'</span><span>'+c.s+'</span></div>';}
  function draw(){var msg='';if(state==='result'){var sc=handScore();chips+=sc[2];msg='<div style="color:#1FCC7C;font-size:11px;margin-bottom:8px">'+sc[1]+(sc[2]?' +'+sc[2]+' chips':'')+'</div>';}
    d.innerHTML='<div style="font-size:11px;color:rgba(255,255,255,.4);margin-bottom:10px">Chips: '+chips+' · 5-Card Draw</div>'+msg+
    '<div style="display:flex;gap:6px;justify-content:center;margin-bottom:10px">'+hand.map(card).join('')+'</div>'+
    (state==='hold'?'<div style="font-size:9px;color:rgba(255,255,255,.25);margin-bottom:8px">Click cards to hold · then draw</div>'+
    '<button onclick="window._draw()" style="padding:7px 20px;background:rgba(31,204,124,.1);border:1px solid rgba(31,204,124,.3);color:#1FCC7C;font-family:monospace;font-size:11px;cursor:pointer;border-radius:3px">Draw (-5)</button>'
    :'<button onclick="window._deal()" style="padding:7px 20px;background:rgba(31,204,124,.1);border:1px solid rgba(31,204,124,.3);color:#1FCC7C;font-family:monospace;font-size:11px;cursor:pointer;border-radius:3px">New Deal</button>');}
  window._hld=function(i){if(state!=='hold')return;held[i]=!held[i];draw();};
  window._draw=function(){if(chips<5)return;chips-=5;hand=hand.map(function(c,i){return held[i]?c:deck.pop()||newDeck().pop();});state='result';draw();};
  window._deal=function(){deck=newDeck();hand=deck.splice(0,5);held=new Array(5).fill(false);state='hold';draw();};
  init();el._fkCleanup=function(){delete window._hld;delete window._draw;delete window._deal;};
}};

/* YAHTZEE */
G.yahtzee={title:'Yahtzee',cat:'cards',render:function(el){
  el.innerHTML='';var d=document.createElement('div');d.style.cssText='padding:12px;font-family:monospace;';el.appendChild(d);
  var dice,held,rolls,scores,CATS=['Ones','Twos','Threes','Fours','Fives','Sixes','3 of a Kind','4 of a Kind','Full House','Sm Straight','Lg Straight','Yahtzee','Chance'];
  function init(){dice=new Array(5).fill(1);held=new Array(5).fill(false);rolls=0;scores={};CATS.forEach(function(c){scores[c]=null;});}
  function roll(){if(rolls>=3)return;dice=dice.map(function(d,i){return held[i]?d:1+rnd(6);});rolls++;draw();}
  function calcScore(cat){var ns=dice.slice().sort(function(a,b){return a-b;});var counts={};ns.forEach(function(n){counts[n]=(counts[n]||0)+1;});var cv=Object.values(counts).sort(function(a,b){return b-a;});
    var idx=['Ones','Twos','Threes','Fours','Fives','Sixes'].indexOf(cat);if(idx>=0)return dice.filter(function(d){return d===idx+1;}).reduce(function(s,d){return s+d;},0);
    if(cat==='3 of a Kind')return cv[0]>=3?dice.reduce(function(a,b){return a+b;},0):0;
    if(cat==='4 of a Kind')return cv[0]>=4?dice.reduce(function(a,b){return a+b;},0):0;
    if(cat==='Full House')return(cv[0]===3&&cv[1]===2)?25:0;
    if(cat==='Sm Straight'){var u=Array.from(new Set(ns));return(u.includes(1)&&u.includes(2)&&u.includes(3)&&u.includes(4))||(u.includes(2)&&u.includes(3)&&u.includes(4)&&u.includes(5))||(u.includes(3)&&u.includes(4)&&u.includes(5)&&u.includes(6))?30:0;}
    if(cat==='Lg Straight')return JSON.stringify(ns)===JSON.stringify([1,2,3,4,5])||JSON.stringify(ns)===JSON.stringify([2,3,4,5,6])?40:0;
    if(cat==='Yahtzee')return cv[0]===5?50:0;
    if(cat==='Chance')return dice.reduce(function(a,b){return a+b;},0);return 0;}
  function score(cat){if(scores[cat]!==null||rolls===0)return;scores[cat]=calcScore(cat);dice=new Array(5).fill(1);held=new Array(5).fill(false);rolls=0;draw();}
  function total(){return Object.values(scores).reduce(function(s,v){return s+(v||0);},0);}
  function allScored(){return CATS.every(function(c){return scores[c]!==null;});}
  function draw(){var FACE=['','⚀','⚁','⚂','⚃','⚄','⚅'];
    d.innerHTML='<div style="display:flex;gap:8px;justify-content:center;margin-bottom:10px">'+
    dice.map(function(dv,i){return'<div onclick="window._hld2('+i+')" style="width:36px;height:36px;background:'+(held[i]?'rgba(31,204,124,.2)':'rgba(255,255,255,.06)')+';border:1px solid '+(held[i]?'rgba(31,204,124,.4)':'rgba(255,255,255,.12)')+';border-radius:5px;font-size:22px;line-height:36px;text-align:center;cursor:pointer">'+FACE[dv]+'</div>';}).join('')+'</div>'+
    '<div style="text-align:center;margin-bottom:8px"><button '+(rolls>=3||allScored()?'disabled':'')+' onclick="window._roll()" style="padding:6px 16px;background:rgba(31,204,124,.1);border:1px solid rgba(31,204,124,.3);color:#1FCC7C;font-family:monospace;font-size:10px;cursor:pointer;border-radius:3px;margin-right:6px">🎲 Roll ('+(3-rolls)+' left)</button></div>'+
    '<div style="display:grid;grid-template-columns:1fr 1fr;gap:3px">'+CATS.map(function(c){var s=scores[c];var pv=rolls>0&&s===null?calcScore(c):null;return'<div onclick="window._sc(\''+c+'\')" style="padding:4px 6px;background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.06);border-radius:3px;cursor:'+(s===null&&rolls>0?'pointer':'default')+';font-size:9px;display:flex;justify-content:space-between"><span style="color:rgba(255,255,255,.4)">'+c+'</span><span style="color:'+(s!==null?'#1FCC7C':pv!==null?'rgba(245,166,35,.6)':'rgba(255,255,255,.2)')+'">'+( s!==null?s:pv!==null?'('+pv+')':'—')+'</span></div>';}).join('')+'</div>'+
    '<div style="text-align:right;font-size:11px;color:rgba(255,255,255,.5);margin-top:6px">Total: '+total()+'</div>'+
    (allScored()?'<button onclick="window._yNew()" style="margin-top:8px;padding:6px 14px;background:rgba(31,204,124,.1);border:1px solid rgba(31,204,124,.3);color:#1FCC7C;font-family:monospace;font-size:10px;cursor:pointer;border-radius:3px">New Game</button>':'');}
  window._hld2=function(i){if(rolls===0)return;held[i]=!held[i];draw();};
  window._roll=roll;window._sc=score;window._yNew=function(){init();draw();};
  init();draw();el._fkCleanup=function(){delete window._hld2;delete window._roll;delete window._sc;delete window._yNew;};
}};

}();
