import { useCallback, useEffect, useState } from 'react'
import { emptyData, storageKey } from './Wellness'
import type { WellnessData } from './Wellness'

type LocalProfile = { id: string; nickname: string; data: WellnessData }
type ProfileStore = { version: 2; activeId: string; profiles: LocalProfile[] }
const createProfile = (nickname: string): LocalProfile => ({ id: crypto.randomUUID(), nickname, data: emptyData() })
function load(): { store: ProfileStore; persist: boolean; error: string } {
  const initial = createProfile('나의 프로필')
  const fallback: ProfileStore = { version: 2, activeId: initial.id, profiles: [initial] }
  try {
    const raw = localStorage.getItem(storageKey)
    if (!raw) return { store: fallback, persist: false, error: '' }
    const parsed = JSON.parse(raw)
    if (parsed.version === 2 && Array.isArray(parsed.profiles) && parsed.profiles.length
        && parsed.profiles.every((p: LocalProfile) => typeof p.id === 'string' && typeof p.nickname === 'string' && Array.isArray(p.data?.records))
        && parsed.profiles.some((p: LocalProfile) => p.id === parsed.activeId)) {
      return { store: parsed, persist: true, error: '' }
    }
    // 이전 단일 프로필 기록을 덮어쓰거나 버리지 않고 첫 로컬 프로필로 옮긴다.
    if (Array.isArray(parsed.records)) {
      initial.data = { ...emptyData(), ...parsed }
      return { store: fallback, persist: true, error: '' }
    }
    return { store: fallback, persist: false, error: '저장된 기록 형식을 읽지 못했습니다. 기존 저장본은 변경하지 않았습니다.' }
  } catch {
    return { store: fallback, persist: false, error: '브라우저 기록을 읽지 못했습니다. 기존 저장본은 변경하지 않았습니다.' }
  }
}
export function useLocalProfiles() {
  const [initial] = useState(load)
  const [store, setStore] = useState(initial.store)
  const [persist, setPersist] = useState(initial.persist)
  const [storageError, setStorageError] = useState(initial.error)
  const [storageTouched, setStorageTouched] = useState(!initial.error)
  useEffect(() => {
    if (!storageTouched) return
    try {
      if (persist) localStorage.setItem(storageKey, JSON.stringify(store))
      else localStorage.removeItem(storageKey)
      setStorageError('')
    } catch { setStorageError('브라우저 보관에 실패했습니다. 현재 실행 중인 기록만 유지됩니다.') }
  }, [store, persist, storageTouched])
  const active = store.profiles.find(p => p.id === store.activeId)!
  // 응답 대기 중 프로필을 전환해도 요청을 시작한 프로필만 갱신한다.
  const setData = useCallback((data: WellnessData) => {
    setStore(s => ({ ...s, profiles: s.profiles.map(p => p.id === active.id ? { ...p, data } : p) }))
  }, [active.id])
  function register(nickname: string) {
    const value = nickname.trim()
    if (!value || value.length > 20) return
    const profile = createProfile(value)
    setStore(s => ({ ...s, activeId: profile.id, profiles: [...s.profiles, profile] }))
  }
  return { data: active.data, setData, activeId: active.id, profiles: store.profiles,
    register, select: (id: string) => setStore(s => s.profiles.some(p => p.id === id) ? { ...s, activeId: id } : s),
    persist, setPersist: (value: boolean) => { setStorageTouched(true); setPersist(value) }, storageError }
}
