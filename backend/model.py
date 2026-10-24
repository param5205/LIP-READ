import torch.nn as nn


class LipReader(nn.Module):
    def __init__(self, num_classes, in_channels=1, hidden=256):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv3d(in_channels, 32, (3, 5, 5), stride=(1, 2, 2), padding=(1, 2, 2)),
            nn.BatchNorm3d(32), nn.ReLU(inplace=True),
            nn.MaxPool3d((1, 2, 2)),                      # 96 -> 48 -> 24

            nn.Conv3d(32, 64, 3, padding=1),
            nn.BatchNorm3d(64), nn.ReLU(inplace=True),
            nn.MaxPool3d((1, 2, 2)),                      # 24 -> 12

            nn.Conv3d(64, 96, 3, padding=1),
            nn.BatchNorm3d(96), nn.ReLU(inplace=True),
            nn.MaxPool3d((1, 2, 2)),                      # 12 -> 6
        )
        self.gru = nn.GRU(
            96 * 6 * 6, hidden, num_layers=2,
            bidirectional=True, batch_first=True, dropout=0.3,
        )
        self.fc = nn.Linear(hidden * 2, num_classes)

    def forward(self, x):
        x = self.conv(x)                                   # (B, 96, T, 6, 6)
        b, c, t, h, w = x.shape
        x = x.permute(0, 2, 1, 3, 4).reshape(b, t, c * h * w)
        x, _ = self.gru(x)
        return self.fc(x)                                  # (B, T, num_classes)