import type {Job,Profile} from './types';
async function request<T>(url:string, options?:RequestInit):Promise<T>{const response=await fetch(url,options);const data=await response.json();if(!response.ok)throw new Error(data.detail||`HTTP ${response.status}`);return data}
export const api={
  jobs:()=>request<Job[]>('/api/jobs'),
  update:(id:string,values:Record<string,unknown>)=>request(`/api/jobs/${id}`,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({values})}),
  retry:(id:string)=>request(`/api/jobs/${id}/retry`,{method:'POST'}),
  remove:(id:string)=>request(`/api/jobs/${id}`,{method:'DELETE'}),
  importJson:(data:unknown)=>request<{inserted:number;updated:number;skipped:number}>('/api/import',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)}),
  chat:(question:string)=>request<{answer:string;sources:Array<{ref:string;company_name?:string;role_title?:string;source_url:string}>}>('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question})}),
  profile:()=>request<Profile>('/api/profile'),
  saveProfile:(profile:Profile)=>request('/api/profile',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(profile)})
};
