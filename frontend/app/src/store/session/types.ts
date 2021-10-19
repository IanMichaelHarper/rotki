import { NumericString, BigNumber } from '@rotki/common';
import { TimeFramePeriod } from '@rotki/common/lib/settings/graphs';
import { z } from 'zod';
import {
  QueriedAddresses,
  Watcher,
  WatcherTypes
} from '@/services/session/types';
import { AccountingSettings, GeneralSettings, Tags } from '@/typing/types';

export interface SessionState {
  newAccount: boolean;
  logged: boolean;
  loginComplete: boolean;
  username: string;
  generalSettings: GeneralSettings;
  accountingSettings: AccountingSettings;
  premium: boolean;
  premiumSync: boolean;
  privacyMode: boolean;
  scrambleData: boolean;
  nodeConnection: boolean;
  syncConflict: SyncConflict;
  tags: Tags;
  watchers: Watcher<WatcherTypes>[];
  queriedAddresses: QueriedAddresses;
  ignoredAssets: string[];
  lastBalanceSave: number;
  lastDataUpload: number;
  timeframe: TimeFramePeriod;
}

export interface SyncConflictPayload {
  readonly localSize: string;
  readonly remoteSize: string;
  readonly localLastModified: number;
  readonly remoteLastModified: number;
}

export interface SyncConflict {
  readonly message: string;
  readonly payload: SyncConflictPayload | null;
}

export interface PremiumCredentialsPayload {
  readonly username: string;
  readonly apiKey: string;
  readonly apiSecret: string;
}

export interface ChangePasswordPayload {
  readonly currentPassword: string;
  readonly newPassword: string;
}

const NftCollectionInfo = z.object({
  bannerImage: z.string().nullable(),
  description: z.string().nullable(),
  name: z.string().nullable(),
  largeImage: z.string().nullable()
});

const Nft = z.object({
  tokenIdentifier: z.string().nonempty(),
  name: z.string().nullable(),
  collection: NftCollectionInfo,
  backgroundColor: z.string().nullable(),
  imageUrl: z.string().nullable(),
  externalLink: z.string().nullable(),
  permalink: z.string().nullable(),
  priceEth: NumericString,
  priceUsd: NumericString
});

export type Nft = z.infer<typeof Nft>;

export type GalleryNft = Omit<Nft, 'priceEth'> & {
  address: string;
  priceInAsset: BigNumber;
  priceAsset: string;
};

const Nfts = z.record(z.array(Nft));

export type Nfts = z.infer<typeof Nfts>;

export const NftResponse = z.object({
  addresses: Nfts,
  entriesFound: z.number(),
  entriesLimit: z.number()
});

export type NftResponse = z.infer<typeof NftResponse>;
