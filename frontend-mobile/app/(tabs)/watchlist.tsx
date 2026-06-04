import { View, Text, FlatList, TouchableOpacity, RefreshControl, ActivityIndicator, Alert, Modal, TextInput, Pressable } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useAuth } from '@/contexts/AuthContext';
import { useRouter, useFocusEffect } from 'expo-router';
import { useState, useCallback } from 'react';
import { watchlistApi, marketApi } from '@/lib/api';
import { Star, Trash2, ChevronDown, Plus, X } from 'lucide-react-native';
import { COLORS, formatCurrency, formatPct } from '@/lib/constants';
import * as Haptics from 'expo-haptics';
import EmptyState from '@/components/ui/EmptyState';

interface WatchlistItem {
  symbol: string;
  price?: number;
  change_pct?: number;
  name?: string;
  source?: 'manual' | 'ai';
}

interface WatchlistListInfo {
  id: string;
  name: string;
  list_type: string;
  item_count: number;
}

export default function WatchlistScreen() {
  const { user } = useAuth();
  const router = useRouter();
  const [lists, setLists] = useState<WatchlistListInfo[]>([]);
  const [selectedListId, setSelectedListId] = useState<string | null>(null);
  const [items, setItems] = useState<WatchlistItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [showListPicker, setShowListPicker] = useState(false);
  const [showNewList, setShowNewList] = useState(false);
  const [newListName, setNewListName] = useState('');

  const fetchLists = useCallback(async () => {
    if (!user) return;
    try {
      const data = await watchlistApi.getLists(user.id);
      const fetched: WatchlistListInfo[] = data.lists || [];
      setLists(fetched);
      return fetched;
    } catch {
      setLists([]);
      return [];
    }
  }, [user]);

  const fetchItems = useCallback(async (listId: string) => {
    if (!user) return;
    try {
      const data = await watchlistApi.getWatchlist(user.id, listId);
      const rawItems: any[] = data.symbols || data.watchlist || [];

      if (rawItems.length > 0 && typeof rawItems[0] === 'object') {
        setItems(rawItems.map((item: any) => ({
          symbol: item.symbol,
          price: item.price,
          change_pct: item.changesPercentage ?? item.change_pct,
          name: item.name,
          source: item.source,
        })));
      } else {
        const symbols: string[] = rawItems.map((s: any) => typeof s === 'string' ? s : s.symbol);
        if (symbols.length > 0) {
          try {
            const quotes = await marketApi.getBatchQuotes(symbols);
            const quoteMap = new Map(
              (quotes.quotes || quotes || []).map((q: any) => [q.symbol, q])
            );
            setItems(symbols.map(s => {
              const q = quoteMap.get(s) as any;
              return {
                symbol: s,
                price: q?.price,
                change_pct: q?.changesPercentage ?? q?.change_pct,
                name: q?.name,
              };
            }));
          } catch {
            setItems(symbols.map(s => ({ symbol: s })));
          }
        } else {
          setItems([]);
        }
      }
    } catch {
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, [user]);

  useFocusEffect(useCallback(() => {
    setLoading(true);
    fetchLists().then(fetched => {
      if (fetched && fetched.length > 0) {
        const listId = selectedListId && fetched.some(l => l.id === selectedListId)
          ? selectedListId
          : fetched[0].id;
        setSelectedListId(listId);
        fetchItems(listId);
      } else {
        setLoading(false);
      }
    });
  }, [fetchLists]));

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    const fetched = await fetchLists();
    if (selectedListId) await fetchItems(selectedListId);
    setRefreshing(false);
  }, [fetchLists, fetchItems, selectedListId]);

  const removeSymbol = (symbol: string) => {
    if (!user) return;
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
    Alert.alert('Remove', `Remove ${symbol} from this list?`, [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Remove',
        style: 'destructive',
        onPress: async () => {
          try {
            await watchlistApi.removeSymbol(user.id, symbol, selectedListId || undefined);
            setItems(prev => prev.filter(i => i.symbol !== symbol));
            fetchLists();
          } catch {}
        },
      },
    ]);
  };

  const handleSelectList = (listId: string) => {
    setSelectedListId(listId);
    setShowListPicker(false);
    setLoading(true);
    fetchItems(listId);
  };

  const handleCreateList = async () => {
    if (!user || !newListName.trim()) return;
    try {
      const data = await watchlistApi.createList(user.id, newListName.trim());
      if (data.list) {
        setLists(prev => [...prev, data.list]);
        setSelectedListId(data.list.id);
        setItems([]);
      }
      setNewListName('');
      setShowNewList(false);
      setShowListPicker(false);
    } catch {}
  };

  const handleDeleteList = (list: WatchlistListInfo) => {
    if (!user) return;
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
    Alert.alert('Delete List', `Delete "${list.name}" and all its items?`, [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Delete',
        style: 'destructive',
        onPress: async () => {
          try {
            await watchlistApi.deleteList(user.id, list.id);
            const remaining = lists.filter(l => l.id !== list.id);
            setLists(remaining);
            if (selectedListId === list.id) {
              const next = remaining[0];
              setSelectedListId(next?.id || null);
              if (next) fetchItems(next.id);
              else setItems([]);
            }
          } catch {}
        },
      },
    ]);
  };

  const selectedList = lists.find(l => l.id === selectedListId);

  return (
    <SafeAreaView className="flex-1 bg-[#fafaf9]" edges={['top']}>
      <View className="px-5 pt-2 pb-3">
        <Text className="text-2xl font-body-bold text-gray-900 mb-3">Watchlist</Text>

        {/* List selector */}
        <TouchableOpacity
          onPress={() => setShowListPicker(true)}
          className="flex-row items-center justify-between bg-gray-50 border border-gray-200 rounded-xl px-3 py-2.5"
          activeOpacity={0.7}
        >
          <View className="flex-row items-center gap-2">
            {selectedList?.list_type === 'ai_picks' && (
              <View className="px-1.5 py-0.5 rounded bg-violet-50 border border-violet-100">
                <Text className="text-[10px] font-body-bold text-violet-500">AI</Text>
              </View>
            )}
            <Text className="text-sm font-body-medium text-gray-900">{selectedList?.name || 'Select list'}</Text>
            <Text className="text-xs font-body text-gray-400">({items.length})</Text>
          </View>
          <ChevronDown size={16} color={COLORS.gray400} />
        </TouchableOpacity>
      </View>

      {loading ? (
        <View className="flex-1 items-center justify-center">
          <ActivityIndicator size="large" color={COLORS.gray900} />
        </View>
      ) : items.length === 0 ? (
        <EmptyState
          icon={<Star size={48} color="#cbd5e1" />}
          title="No stocks in this list"
          description="Search for stocks and add them to your watchlist"
          actionLabel="Search Stocks"
          onAction={() => router.push('/(tabs)' as any)}
        />
      ) : (
        <FlatList
          data={items}
          keyExtractor={(item) => item.symbol}
          contentContainerClassName="px-5 pb-4"
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
          renderItem={({ item }) => (
            <TouchableOpacity
              onPress={() => router.push(`/stock/${item.symbol}`)}
              className="bg-white rounded-2xl p-4 mb-2.5 border border-gray-200 flex-row items-center justify-between"
              activeOpacity={0.7}
            >
              <View className="flex-1 mr-3">
                <View className="flex-row items-center gap-1.5">
                  <Text className="text-[15px] font-body-bold text-gray-900">{item.symbol}</Text>
                </View>
                {item.name && (
                  <Text className="text-sm font-body text-gray-500 mt-0.5" numberOfLines={1}>{item.name}</Text>
                )}
              </View>
              <View className="flex-row items-center gap-3">
                {item.price != null && (
                  <View className="items-end">
                    <Text className="text-[15px] font-body-medium text-gray-900 tabular-nums">
                      {formatCurrency(item.price, false, item.symbol)}
                    </Text>
                    {item.change_pct != null && (
                      <Text className={`text-sm font-body tabular-nums ${item.change_pct >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                        {formatPct(item.change_pct)}
                      </Text>
                    )}
                  </View>
                )}
                <TouchableOpacity onPress={() => removeSymbol(item.symbol)} className="p-1.5" activeOpacity={0.7}>
                  <Trash2 size={16} color={COLORS.gray400} />
                </TouchableOpacity>
              </View>
            </TouchableOpacity>
          )}
        />
      )}

      {/* List picker modal */}
      <Modal visible={showListPicker} transparent animationType="slide">
        <Pressable className="flex-1 bg-black/30" onPress={() => { setShowListPicker(false); setShowNewList(false); }}>
          <View className="flex-1" />
          <Pressable onPress={() => {}} className="bg-white rounded-t-3xl px-5 pt-4 pb-8">
            <View className="w-10 h-1 rounded-full bg-gray-200 self-center mb-4" />
            <Text className="text-lg font-body-bold text-gray-900 mb-4">Select List</Text>

            {lists.map(list => (
              <TouchableOpacity
                key={list.id}
                onPress={() => handleSelectList(list.id)}
                className={`flex-row items-center justify-between px-4 py-3.5 rounded-xl mb-1.5 ${list.id === selectedListId ? 'bg-gray-50' : ''}`}
                activeOpacity={0.7}
              >
                <View className="flex-row items-center gap-2 flex-1">
                  {list.list_type === 'ai_picks' && (
                    <View className="px-1 py-px rounded bg-violet-50 border border-violet-100">
                      <Text className="text-[9px] font-body-bold text-violet-500">AI</Text>
                    </View>
                  )}
                  <Text className="text-[15px] font-body-medium text-gray-900">{list.name}</Text>
                  <Text className="text-xs font-body text-gray-400">({list.item_count})</Text>
                </View>
                {list.list_type === 'custom' && (
                  <TouchableOpacity onPress={() => handleDeleteList(list)} className="p-1.5" activeOpacity={0.7}>
                    <X size={14} color={COLORS.gray400} />
                  </TouchableOpacity>
                )}
              </TouchableOpacity>
            ))}

            {/* Create new list */}
            <View className="border-t border-gray-100 mt-2 pt-3">
              {showNewList ? (
                <View className="flex-row items-center gap-2">
                  <TextInput
                    value={newListName}
                    onChangeText={setNewListName}
                    onSubmitEditing={handleCreateList}
                    placeholder="List name..."
                    className="flex-1 px-3 py-2.5 text-sm bg-gray-50 rounded-xl border border-gray-200"
                    autoFocus
                  />
                  <TouchableOpacity
                    onPress={handleCreateList}
                    disabled={!newListName.trim()}
                    className="bg-emerald-600 px-4 py-2.5 rounded-xl"
                    activeOpacity={0.7}
                  >
                    <Text className="text-sm font-body-bold text-white">Add</Text>
                  </TouchableOpacity>
                  <TouchableOpacity onPress={() => { setShowNewList(false); setNewListName(''); }} className="p-2" activeOpacity={0.7}>
                    <X size={16} color={COLORS.gray400} />
                  </TouchableOpacity>
                </View>
              ) : (
                <TouchableOpacity
                  onPress={() => setShowNewList(true)}
                  className="flex-row items-center gap-2 px-4 py-3"
                  activeOpacity={0.7}
                >
                  <Plus size={16} color={COLORS.gray500} />
                  <Text className="text-sm font-body text-gray-500">New list</Text>
                </TouchableOpacity>
              )}
            </View>
          </Pressable>
        </Pressable>
      </Modal>
    </SafeAreaView>
  );
}
