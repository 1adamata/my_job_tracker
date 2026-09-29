import {FormEvent,useEffect,useState} from 'react';
import {Check,FileText,Save,UserRound} from 'lucide-react';
import {api} from '../api';
import {PageHeader} from '../components/PageHeader';
import type {Profile} from '../types';

const blank:Profile={
  name:'Nurassyl Molshin',headline:'Computer Science student · Data & AI',location:'Manchester / Astana',
  target_roles:'Data Science, Machine Learning, Data Engineering, AI Engineering',
  skills:'Python, SQL, Machine Learning, Data Analysis, FastAPI, React',visa_context:'',summary:'',cv_text:''
};

export function ProfilePage(){
  const [profile,setProfile]=useState<Profile>(blank);const [saved,setSaved]=useState(false);
  useEffect(()=>{api.profile().then(p=>setProfile({...p,name:p.name||blank.name,headline:p.headline||blank.headline,location:p.location||blank.location,target_roles:p.target_roles||blank.target_roles,skills:p.skills||blank.skills}))},[]);
  const set=(key:keyof Profile,value:string)=>setProfile(current=>({...current,[key]:value}));
  const save=async(event:FormEvent)=>{event.preventDefault();await api.saveProfile(profile);setSaved(true);setTimeout(()=>setSaved(false),1800)};
  return <><PageHeader eyebrow="CANDIDATE PROFILE" title="Your matching profile" description="The AI assistant uses this context when comparing vacancies with your background."/><div className="profile-grid"><aside className="profile-card"><div className="profile-avatar"><UserRound/></div><h2>{profile.name||'Your name'}</h2><p>{profile.headline||'Add a professional headline'}</p><span>{profile.location}</span><div className="profile-hint"><FileText/><p><strong>Private and local</strong>Your profile and CV text stay in the SQLite database on this computer.</p></div></aside><form className="panel profile-form" onSubmit={save}><div className="field-grid"><label>Name<input value={profile.name} onChange={e=>set('name',e.target.value)}/></label><label>Headline<input value={profile.headline} onChange={e=>set('headline',e.target.value)}/></label><label>Location<input value={profile.location} onChange={e=>set('location',e.target.value)}/></label><label>Visa context<input value={profile.visa_context} onChange={e=>set('visa_context',e.target.value)}/></label><label className="span-2">Target roles<textarea rows={2} value={profile.target_roles} onChange={e=>set('target_roles',e.target.value)}/></label><label className="span-2">Skills<textarea rows={3} value={profile.skills} onChange={e=>set('skills',e.target.value)}/></label><label className="span-2">Professional summary<textarea rows={4} value={profile.summary} onChange={e=>set('summary',e.target.value)}/></label><label className="span-2">Master CV text<textarea rows={10} value={profile.cv_text} onChange={e=>set('cv_text',e.target.value)} placeholder="Paste the plain text of your current CV here for grounded job matching…"/></label></div><button className="primary-btn" type="submit">{saved?<><Check size={16}/>Saved</>:<><Save size={16}/>Save profile</>}</button></form></div></>}
